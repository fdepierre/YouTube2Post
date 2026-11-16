#!/usr/bin/env python3
"""
YouTube to Post Converter
------------------------
This script processes YouTube videos or local .mp3 files, transcribes them, and enables AI-powered chat interactions
based on the content. It supports three main operations:
- Transcription only: Downloads and transcribes a YouTube video, or transcribes a local .mp3 file
- Chat only: Initiates a chat session based on an existing transcript
- Full process: Combines both operations (download, transcribe, and chat)

Usage:
    python yt2post.py (-t | -c | -f) [-m] [-v] [-p MODE] [-j] [<youtube_url_or_file>]

Arguments:
    <youtube_url_or_file>   URL of the YouTube video or path to a local .mp3 file to process
                            (with -t or -f, taken from the clipboard if omitted), or the
                            transcript file to chat about (-c).

Notes:
- Only local .mp3 files are supported for direct audio transcription (other formats must be converted to mp3 first).
- Metadata (title, author, description) is automatically extracted from the mp3 if present, or defaults are used.
"""

import argparse
import gc
import json
import os
import sys

import argcomplete

from modules.config_manager import ConfigManager
from modules.directory_manager import DirectoryManager
from modules.youtube_downloader import YouTubeDownloader, has_video, playlist_id
from modules.transcriber import Transcriber, transcript_path
from modules.source_export import (PlaylistRecord, file_source, transcription_settings,
                                   write_source, youtube_source)
from modules.ollama_manager import OllamaManager
from modules.clipboard import youtube_url_from_clipboard, write_clipboard
from modules import ui
from modules import sysinfo

# config.json and its relative directories are relative to this script, so the
# program can be started from any directory (e.g. through a shell alias).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -p/--playlist: what to do with a link to a playlist
PLAYLIST_MODES = ('video', 'separate', 'combined')


def project_path(path):
    """Return path as an absolute path, relative ones being taken from BASE_DIR."""
    return os.path.normpath(os.path.join(BASE_DIR, os.path.expanduser(path)))


def get_input_from_clipboard_or_prompt():
    """Return the YouTube URL in the clipboard, or ask the user for a URL or mp3 file."""
    url = youtube_url_from_clipboard()
    if url:
        print(f"Using YouTube URL from clipboard: {ui.style(url, 'bold')}")
        return url
    try:
        value = input(ui.style("No YouTube URL in the clipboard. ", 'yellow')
                      + "Enter a YouTube URL or .mp3 file: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(1)
    if not value:
        ui.error("No input given.")
        sys.exit(1)
    return value


def main():
    # Initialize argument parser with program description
    parser = argparse.ArgumentParser(
        description='Process YouTube videos (via URL) or local .mp3 files: download, transcribe, and chat with AI.\n'
                    'Input can be a YouTube URL or a path to a local .mp3 file. Only .mp3 is supported for local audio.'
    )
    parser.add_argument('-t', '--transcribe', help='Download and transcribe the YouTube video or local mp3 file', action='store_true')
    parser.add_argument('-c', '--chat', help='Chat with AI based on the transcript.', action='store_true')
    parser.add_argument('-f', '--full', help='Download, transcribe, and chat with AI.', action='store_true')
    parser.add_argument('-m', '--model-select', help='Choose the Ollama model from the installed ones (default: the loaded model, or the only installed one)', action='store_true')
    parser.add_argument('-v', '--verbose', help="Show the detailed log of each step (e.g. yt-dlp's)", action='store_true')
    parser.add_argument('-p', '--playlist', choices=PLAYLIST_MODES,
                        help='For a link to a playlist, what to transcribe without asking: the linked '
                             'video only, every video in its own file, or every video in one file')
    parser.add_argument('-j', '--json', action='store_true',
                        help='Also save each transcript as JSON with the start and end time of every '
                             'passage (work/sources/), for other programs')
    parser.add_argument('-n', '--max-videos', type=int, metavar='N',
                        help='For a playlist with -j: transcribe at most N videos not transcribed '
                             'yet, then stop (run again for the next ones)')
    parser.add_argument('--redo', action='store_true',
                        help='For a playlist with -j: transcribe again the videos already done')
    parser.add_argument('url_or_input', help='URL of the YouTube video or input file (mp3 or text) for processing. '
                        'With -t or -f, if omitted, the YouTube URL is taken from the clipboard.', nargs='?')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ui.verbose = args.verbose

    if not (args.transcribe or args.chat or args.full):
        parser.print_help()
        sys.exit(1)

    # No URL given: take the YouTube URL from the clipboard, or ask for it
    if (args.transcribe or args.full) and not args.url_or_input:
        args.url_or_input = get_input_from_clipboard_or_prompt()
    if args.chat and not (args.transcribe or args.full):
        if not args.url_or_input:
            parser.error("-c needs the transcript file to chat about")
        if not os.path.isfile(args.url_or_input):
            parser.error(f"transcript file not found: {args.url_or_input}")

    try:
        run(args)
    except KeyboardInterrupt:
        ui.error("\n✖ Interrupted.")
        sys.exit(1)
    except Exception as e:
        ui.error(f"\n✖ Error: {e}")
        sys.exit(1)


def is_local_mp3(path):
    return bool(path) and path.lower().endswith('.mp3') and os.path.isfile(path)


def mp3_metadata_file(mp3_file, tmp_dir):
    """Write the metadata JSON of a local mp3 file (from its ID3 tags) and return its path."""
    base = os.path.splitext(os.path.basename(mp3_file))[0]
    try:
        from mutagen.easyid3 import EasyID3
        tags = EasyID3(mp3_file)
        title = tags.get('title', [base])[0]
        author = tags.get('artist', ['Unknown'])[0]
        description = tags.get('comment', [''])[0]
    except Exception:
        title, author, description = base, "Unknown", ""
    json_file = os.path.join(tmp_dir, f"{base}.info.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        # same keys as the YouTube metadata written by yt-dlp
        json.dump({"title": title, "uploader": author, "description": description}, f)
    return json_file


def _total_duration(entries):
    known = [e['duration'] for e in entries if e.get('duration')]
    text = ui.clock(sum(known))
    return text if len(known) == len(entries) else f"at least {text}"


def _ask(question, options, default):
    """Ask a numbered question; without an answer (no terminal), take the default."""
    print(question)
    try:
        index = ui.choose(options, default=default)
    except EOFError:
        index = default
        print(f"\n  (no answer: {options[default]})")
    return index


def choose_playlist_mode(url, playlist, mode, chat):
    """
    Return 'video', 'separate' or 'combined' for a link to a playlist: the
    -p option if given, else the user's answers. A link to a video in a
    playlist first asks whether to take the whole playlist.
    """
    entries = playlist['entries']
    by = f" by {playlist['uploader']}" if playlist.get('uploader') else ""
    print(f"\nThis link is part of the playlist {ui.style(playlist['title'], 'bold')}{by}: "
          f"{len(entries)} videos, {_total_duration(entries)} of audio.")
    if mode == 'video' and not has_video(url):
        raise Exception("This link is a playlist, without a video to choose: "
                        "use -p separate or -p combined")
    if mode:
        return mode
    if has_video(url):
        whole = _ask("What should be transcribed?",
                     ["This video only", f"The whole playlist ({len(entries)} videos)"], 0)
        if not whole:
            return 'video'
    # The chat (-f) reads every transcript: one file is the natural choice
    combined = _ask("How should the transcripts be saved?",
                    ["One file per video", "One file with all the transcripts"], 1 if chat else 0)
    return 'combined' if combined else 'separate'


def run(args):
    """Run the steps of the chosen mode, numbered as they go: [2/4] ..."""
    transcribe = args.transcribe or args.full
    chat = args.chat or args.full
    source = args.url_or_input
    local_mp3 = transcribe and is_local_mp3(source)

    config_manager = ConfigManager(os.path.join(BASE_DIR, 'config.json'))
    tmp_dir = project_path(config_manager.read_config('tmp_directory'))
    work_dir = project_path(config_manager.read_config('work_directory'))
    DirectoryManager(tmp_directory=tmp_dir, work_directory=work_dir)

    timed = getattr(args, 'json', False)
    max_videos, redo = getattr(args, 'max_videos', None), getattr(args, 'redo', False)
    if (max_videos is not None or redo) and not timed:
        raise Exception("-n and --redo need -j: the videos already transcribed are known "
                        "from their JSON files")
    if max_videos is not None and max_videos < 1:
        raise Exception("-n needs a number of videos of at least 1")

    youtube_downloader = None
    if transcribe and not local_mp3:
        youtube_downloader = YouTubeDownloader(tmp_directory=tmp_dir, verbose=args.verbose)

    # A link to a playlist: decide first what to transcribe, so the user can
    # then leave during the long steps
    playlist, mode, linked_playlist = None, None, None
    if youtube_downloader and playlist_id(source):
        playlist = youtube_downloader.playlist_info(source)
        mode = choose_playlist_mode(source, playlist, args.playlist, chat)
        if mode == 'video':
            linked_playlist, playlist = playlist, None
    videos = playlist['entries'] if playlist else []
    if (max_videos is not None or redo) and not playlist:
        raise Exception("-n and --redo are for a whole playlist (-p separate or -p combined)")
    # With -j, the playlist's record tells the videos already transcribed: they are skipped
    record = PlaylistRecord(work_dir, playlist) if playlist and timed else None
    todo = record.to_do(max_videos, redo) if record else list(range(1, len(videos) + 1))
    if record and len(todo) < len(videos):
        done = sum(record.is_done(p) for p in range(1, len(videos) + 1))
        print(f"{done} of {len(videos)} videos already transcribed; "
              f"this run: {len(todo)} video{'s' if len(todo) != 1 else ''}.")
        if not todo:
            ui.success("\nEvery video of the playlist is already transcribed (--redo to do them again).")
            ui.note(f"Playlist record (state of each video): {os.path.relpath(record.path, work_dir)}")
            return

    names = []
    if chat:
        names.append("Choosing the Ollama model")
    if transcribe:
        names.append("Loading the transcription model")
        if playlist:
            names += [f"Video {i}/{len(videos)}: {_short(videos[i - 1]['title'])}" for i in todo]
        else:
            if not local_mp3:
                names.append("Downloading the audio from YouTube")
            names.append("Transcribing the audio")
    if chat:
        names.append("Chatting about the transcript" + ("s" if playlist else ""))
    steps = ui.Steps(names)

    if ui.verbose:
        print(f"\n{ui.style('System', 'bold')}")
        for line in sysinfo.system_details():
            ui.detail(line)

    chat_manager = None
    if chat:
        steps.next()
        model_name = OllamaManager().choose_model(ask=args.model_select)
        steps.done(f"Ollama model: {ui.style(model_name, 'bold')}")
        chat_manager = OllamaManager(model=model_name)

    transcript_file = source
    if transcribe:
        steps.next()
        transcriber = Transcriber(work_directory=work_dir, announce=False)
        steps.done(f"{transcriber.model_name} on {transcriber.device.upper()}")

        if playlist:
            transcript_file = transcribe_playlist(steps, transcriber, youtube_downloader, playlist,
                                                  mode, work_dir, tmp_dir, chat, timed=timed,
                                                  record=record, todo=todo)
        else:
            if local_mp3:
                audio_file, json_file = source, mp3_metadata_file(source, tmp_dir)
            else:
                steps.next(source)
                audio_file, json_file = youtube_downloader.download_audio(source)
                title = (youtube_downloader.info or {}).get('title', os.path.basename(audio_file))
                steps.done(f"{ui.style(title, 'bold')}, {youtube_downloader.downloaded_size(audio_file)}")

            steps.next()
            transcript_file = transcriber.create_transcript_content(audio_file, json_file, source)
            steps.done(_transcribed(transcriber))
            source_file = None
            if getattr(args, 'json', False):
                settings = transcription_settings(transcriber)
                if local_mp3:
                    with open(json_file, encoding='utf-8') as f:
                        exported = file_source(audio_file, json.load(f), transcriber.segments, settings)
                else:
                    # A video taken alone from a playlist is still one of its videos
                    in_playlist = PlaylistRecord(work_dir, linked_playlist) if linked_playlist else None
                    position = in_playlist.position_of(youtube_downloader.info['id']) if in_playlist else None
                    exported = youtube_source(youtube_downloader.info, transcriber.segments, settings,
                                              playlist=linked_playlist if position else None,
                                              position=position)
                source_file = write_source(work_dir, exported)
                if not local_mp3 and position:
                    in_playlist.transcribed(position, source_file, youtube_downloader.info.get('title'))
            ui.saved_file("Transcript saved to:", transcript_file, timed=source_file)
            _copy_path(transcript_file)
        # Free the Whisper model's GPU memory for the Ollama model
        del transcriber
        gc.collect()

    if chat:
        steps.next()
        chat_manager.interactive_chat(transcript_file)


def _short(title, width=60):
    return title if len(title) <= width else title[:width - 1] + "…"


def _transcribed(transcriber):
    return (f"{ui.duration(transcriber.audio_duration)} of audio transcribed"
            + (f" ({transcriber.language})" if transcriber.language else ""))


def _copy_path(path):
    """Copy the full path to the clipboard, in the format of where the program
    runs (C:\\... on Windows, /mnt/c/... in WSL), ready to paste."""
    if write_clipboard(os.path.abspath(path)):
        ui.note("Text file path copied to the clipboard")


def transcribe_playlist(steps, transcriber, downloader, playlist, mode, work_dir, tmp_dir, chat,
                        timed=False, record=None, todo=None):
    """
    Download and transcribe the videos of the playlist at the positions
    `todo` (default: with ``timed``, those not done yet; else all), one step
    each. Files are written as each video is done, so an interruption keeps the
    videos already transcribed; a video that fails is skipped. With ``timed``, each
    video's timestamped JSON is saved too, and the state of every video
    (transcribed, failed, pending) in the playlist's record. Returns the file with every
    transcript (for the chat), or None.
    """
    videos = playlist['entries']
    # One file with every transcript: the result in 'combined' mode, and
    # what the chat (-f) reads in 'separate' mode
    combined = None
    if mode == 'combined':
        combined = transcript_path(work_dir, playlist['title'], '_playlist_transcript.txt')
    elif chat:
        combined = transcript_path(tmp_dir, playlist['title'], '_playlist_transcript.txt')
    if record is None and timed:
        record = PlaylistRecord(work_dir, playlist)
    if todo is None:
        todo = record.to_do() if record else list(range(1, len(videos) + 1))
    # Videos skipped as already done are in the file of the earlier runs: add to it
    resumed = len(todo) < len(videos) and combined and os.path.isfile(combined) and mode == 'combined'
    if combined and not resumed:
        with open(combined, 'w', encoding='utf-8') as f:
            f.write(f"The following text contains the transcripts of the {len(videos)} videos of the "
                    f"YouTube playlist \"{playlist['title']}\" from {playlist['url']}\n")

    saved, failed = [], []
    for number in todo:
        video = videos[number - 1]
        steps.next()
        audio_file = None
        try:
            audio_file, json_file = downloader.download_audio(video['url'])
            # The video's own title: the playlist may list a translated one
            real_title = (downloader.info or {}).get('title') or video['title']
            steps.done(f"{ui.style(real_title, 'bold')}, {downloader.downloaded_size(audio_file)}")
            title, content = transcriber.transcript(audio_file, json_file, video['url'])
            steps.done(_transcribed(transcriber))
            if timed:
                source_file = write_source(work_dir, youtube_source(
                    downloader.info, transcriber.segments, transcription_settings(transcriber),
                    playlist=playlist, position=number))
                ui.note(f"With times: {os.path.relpath(source_file, work_dir)}")
                record.transcribed(number, source_file, real_title)
        except Exception as e:
            steps.failed(f"Skipped: {e}")
            if record:
                record.failed(number, e)
            failed.append((number, video['title']))
            continue
        finally:
            if audio_file and os.path.isfile(audio_file):
                os.remove(audio_file)  # a playlist can be gigabytes: free the space as it goes
        if mode == 'separate':
            # Numbered: the files sort in the playlist's order
            path = transcript_path(work_dir, f"{number:0{len(str(len(videos)))}d}_{title}")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            saved.append(path)
        if combined:
            with open(combined, 'a', encoding='utf-8') as f:
                f.write(f"\n\n=== Video {number}/{len(videos)} ===\n\n{content}\n")

    if failed:
        ui.warn(f"\n{len(failed)} of {len(todo)} videos could not be transcribed:")
        for number, title in failed:
            ui.warn(f"  {number}. {title}")
    if record:
        ui.note(f"Playlist record (state of each video): {os.path.relpath(record.path, work_dir)}")
    if record:
        counts = record.counts()
        ui.note(f"Playlist: {counts['transcribed']} of {len(videos)} videos transcribed, "
                f"{counts['failed']} failed, {counts['pending']} not done yet")
    if not todo:
        return combined if mode == 'combined' else None  # every video was already done
    if len(failed) == len(todo):
        raise Exception("No video of the playlist could be transcribed")

    if mode == 'combined':
        ui.saved_file("All the transcripts saved to:", combined)
        _copy_path(combined)
    else:
        ui.saved_files("Transcripts saved to:", saved)
        if write_clipboard(os.path.dirname(os.path.abspath(saved[0]))):
            ui.note("Directory path copied to the clipboard")
    return combined


if __name__ == '__main__':
    main()
