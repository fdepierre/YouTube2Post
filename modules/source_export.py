"""
Source Export Module
--------------------
Writes each transcription as a source file for other programs: the video's
metadata and its timestamped segments, in the "yt2post-source/1" JSON format.

This JSON is the source of truth for the transcript and its timestamps; the
.txt transcript, and what other tools (e.g. ArchivTrace) build from it, are
views of it. One folder per video, one file per version of the transcript:

    <work>/sources/youtube/<Title>_<video_id>/<date>_<model>_<version>.json

for example ``Le_SECRET_le_MIEUX_GARDE_de_nos_ELITES_9ePdrj096XY/
2026-11-14_large-v3-turbo_b7e557.json``. The folder is found again by the
video id, so a video renamed on YouTube keeps its folder. The version is a
fingerprint of the segments and of the transcription settings, so writing the
same transcription again (even another day) changes nothing, and a new
transcription (another model, other settings) is a new file next to the old one.
"""

import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone

SCHEMA = "yt2post-source/1"

_REQUIRED = ("schema", "source_id", "source_type", "title", "collected_at",
             "transcription", "text_version", "segments", "status")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _segments(raw_segments):
    """Number the (start, end, text) segments: s0001, s0002..."""
    return [{"id": f"s{i:04d}", "start": round(float(start), 2), "end": round(float(end), 2),
             "text": text.strip()}
            for i, (start, end, text) in enumerate(raw_segments, 1)]


def transcription_settings(transcriber):
    """The engine, model and parameters that produced a transcription."""
    try:
        from faster_whisper import __version__ as engine_version
    except ImportError:  # pragma: no cover
        engine_version = None
    return {
        "engine": "faster-whisper", "engine_version": engine_version,
        "model": transcriber.model_name, "device": transcriber.device,
        "compute_type": transcriber.compute_type, "batch_size": transcriber.BATCH_SIZE,
        "language": transcriber.language,
        "language_source": "youtube" if transcriber.language_given else "detected",
    }


def text_version(segments, transcription):
    """Fingerprint of the segments and of the settings that produced them."""
    payload = json.dumps({"segments": segments, "transcription": transcription},
                         ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _iso_date(yyyymmdd):
    """yt-dlp's '20240502' as '2024-05-02', or None."""
    if yyyymmdd and len(str(yyyymmdd)) == 8 and str(yyyymmdd).isdigit():
        d = str(yyyymmdd)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return None


def youtube_source(info, raw_segments, transcription, playlist=None, position=None):
    """
    The source of a YouTube video, from yt-dlp's info and the segments.
    `channel` is who published the video: no author is inferred (the channel,
    the speaker and the scientific author are often different people).
    """
    segments = _segments(raw_segments)
    video_id = info["id"]
    source = {
        "schema": SCHEMA,
        "source_id": f"youtube:{video_id}",
        "source_type": "youtube_video",
        "youtube": {"video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}"},
        "title": info.get("title") or video_id,
        "channel": info.get("channel") or info.get("uploader"),
        "published": _iso_date(info.get("upload_date")),
        "collected_at": _now(),
        "language": transcription.get("language"),
        "playlists": [],
        "transcription": transcription,
        "text_version": text_version(segments, transcription),
        "segments": segments,
        "status": {"state": "transcribed", "errors": []},
    }
    if playlist:
        source["playlists"].append({"id": playlist.get("id"), "title": playlist.get("title"),
                                    "position": position})
    return source


def file_source(audio_file, metadata, raw_segments, transcription):
    """The source of a local audio file, identified by its content (not its name)."""
    digest = hashlib.sha256()
    with open(audio_file, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    segments = _segments(raw_segments)
    return {
        "schema": SCHEMA,
        "source_id": f"file:sha256:{digest.hexdigest()}",
        "source_type": "audio_file",
        "file": {"name": os.path.basename(audio_file)},
        "title": metadata.get("title") or os.path.basename(audio_file),
        "channel": None,
        "published": None,
        "collected_at": _now(),
        "language": transcription.get("language"),
        "playlists": [],
        "transcription": transcription,
        "text_version": text_version(segments, transcription),
        "segments": segments,
        "status": {"state": "transcribed", "errors": []},
    }


def validate_source(source):
    """Raise ValueError if the source does not follow the schema."""
    missing = [key for key in _REQUIRED if key not in source]
    if missing:
        raise ValueError(f"source is missing {', '.join(missing)}")
    if source["schema"] != SCHEMA:
        raise ValueError(f"unknown schema {source['schema']!r}")
    previous_start = 0.0
    for segment in source["segments"]:
        if not (0 <= segment["start"] <= segment["end"]):
            raise ValueError(f"segment {segment['id']}: start after end")
        if segment["start"] < previous_start:
            raise ValueError(f"segment {segment['id']}: not in time order")
        previous_start = segment["start"]


# Characters of the version fingerprint shown in a file name
VERSION_CHARS = 6


def readable_name(text, limit=50):
    """'Le SECRET le MIEUX GARDÉ…' -> 'Le_SECRET_le_MIEUX_GARDE…': ASCII letters,
    digits, '-' and '_' only, readable on every system and in any terminal."""
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r'[^A-Za-z0-9\-]+', '_', ascii_text).strip('_-')
    return name[:limit].rstrip('_-')


def _source_folder(work_dir, source):
    """The folder of a video or audio file: the existing one with its id, else a new one."""
    kind, _, identifier = source["source_id"].partition(":")
    parent = os.path.join(work_dir, "sources", "youtube" if kind == "youtube" else "files")
    identifier = identifier.replace("sha256:", "")[:16]
    if os.path.isdir(parent):
        for name in sorted(os.listdir(parent)):
            # '<title>_<id>': the id ends the name; the title may have changed since
            if name.endswith("_" + identifier) and os.path.isdir(os.path.join(parent, name)):
                return os.path.join(parent, name)
    title = readable_name(source.get("title") or "")
    return os.path.join(parent, f"{title}_{identifier}" if title else identifier)


def _version_of(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("text_version")
    except (OSError, ValueError):
        return None


def source_path(work_dir, source):
    """Where a source version is stored: its existing file, else a new one."""
    folder = _source_folder(work_dir, source)
    version = source["text_version"].replace("sha256:", "")
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if (name.endswith(f"_{version[:VERSION_CHARS]}.json")
                    and _version_of(os.path.join(folder, name)) == source["text_version"]):
                return os.path.join(folder, name)  # same transcription, written another day
    model = readable_name(str(source["transcription"].get("model") or "model"), 40)
    name = f"{source['collected_at'][:10]}_{model}_{version[:VERSION_CHARS]}.json"
    if os.path.exists(os.path.join(folder, name)):  # another version, same short fingerprint
        name = name.replace(f"_{version[:VERSION_CHARS]}.json", f"_{version[:16]}.json")
    return os.path.join(folder, name)


def write_source(work_dir, source):
    """
    Write the source and return its path. The same version is written once:
    if it already exists, only the playlists the video was found in are added
    (a video in two playlists stays one source).
    """
    validate_source(source)
    path = source_path(work_dir, source)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
        known = {p.get("id") for p in existing.get("playlists", [])}
        added = [p for p in source["playlists"] if p.get("id") not in known]
        if not added:
            return path
        existing["playlists"] = existing.get("playlists", []) + added
        source = existing
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(source, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)  # never a half-written source
    return path
