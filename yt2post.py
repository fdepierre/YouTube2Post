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
    python yt2post.py (-t | -c | -f) [-m] [-v] [<youtube_url_or_file>]

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
from modules.youtube_downloader import YouTubeDownloader
from modules.transcriber import Transcriber
from modules.ollama_manager import OllamaManager
from modules.clipboard import youtube_url_from_clipboard, write_clipboard
from modules import ui
from modules import sysinfo

# config.json and its relative directories are relative to this script, so the
# program can be started from any directory (e.g. through a shell alias).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


def run(args):
    """Run the steps of the chosen mode, numbered as they go: [2/4] ..."""
    transcribe = args.transcribe or args.full
    chat = args.chat or args.full
    local_mp3 = transcribe and is_local_mp3(args.url_or_input)

    names = []
    if chat:
        names.append("Choosing the Ollama model")
    if transcribe:
        names.append("Loading the transcription model")
        if not local_mp3:
            names.append("Downloading the audio from YouTube")
        names.append("Transcribing the audio")
    if chat:
        names.append("Chatting about the transcript")
    steps = ui.Steps(names)

    if ui.verbose:
        print(f"\n{ui.style('System', 'bold')}")
        for line in sysinfo.system_details():
            ui.detail(line)

    config_manager = ConfigManager(os.path.join(BASE_DIR, 'config.json'))
    tmp_dir = project_path(config_manager.read_config('tmp_directory'))
    work_dir = project_path(config_manager.read_config('work_directory'))
    DirectoryManager(tmp_directory=tmp_dir, work_directory=work_dir)

    youtube_downloader = None
    if transcribe and not local_mp3:
        youtube_downloader = YouTubeDownloader(tmp_directory=tmp_dir, verbose=args.verbose)

    chat_manager = None
    if chat:
        # Chosen first, so the user can then leave during the long steps
        steps.next()
        model_name = OllamaManager().choose_model(ask=args.model_select)
        steps.done(f"Ollama model: {ui.style(model_name, 'bold')}")
        chat_manager = OllamaManager(model=model_name)

    transcript_file = args.url_or_input
    if transcribe:
        steps.next()
        transcriber = Transcriber(work_directory=work_dir, announce=False)
        steps.done(f"{transcriber.model_name} on {transcriber.device.upper()}")

        source = args.url_or_input
        if local_mp3:
            audio_file, json_file = source, mp3_metadata_file(source, tmp_dir)
        else:
            steps.next(source)
            audio_file, json_file = youtube_downloader.download_audio(source)
            title = (youtube_downloader.info or {}).get('title', os.path.basename(audio_file))
            steps.done(f"{ui.style(title, 'bold')}, {youtube_downloader.downloaded_size(audio_file)}")

        steps.next()
        transcript_file = transcriber.create_transcript_content(audio_file, json_file, source)
        steps.done(f"{ui.duration(transcriber.audio_duration)} of audio transcribed"
                   + (f" ({transcriber.language})" if transcriber.language else ""))
        ui.saved_file("Transcript saved to:", transcript_file)
        # The full path, in the format of where the program runs (C:\... on
        # Windows, /mnt/c/... in WSL), ready to paste
        if write_clipboard(os.path.abspath(transcript_file)):
            ui.note("Full path copied to the clipboard")
        # Free the Whisper model's GPU memory for the Ollama model
        del transcriber
        gc.collect()

    if chat:
        steps.next()
        chat_manager.interactive_chat(transcript_file)


if __name__ == '__main__':
    main()
