# Data lineage

How a transcript travels through YouTube2Post, and which file is authoritative for what.
The format of a piece of information follows **who produces it**: one file is
authoritative, every other form is derived from it, in one direction.

| Information | Produced by | Authoritative file | Derived forms |
|---|---|---|---|
| Transcript: segments with start/end times, video metadata, transcription settings | the program (yt-dlp + faster-whisper) | `work/sources/youtube/<Title>_<video_id>/<date>_<model>_<version>.json` (`yt2post-source/1`) | `work/<title>_transcript.txt`, ArchivTrace notebooks |
| Readable transcript for the chat | the program | — (a view) | `work/<title>_transcript.txt` |
| Chat answers | the LLM (Ollama) | not stored | — |

```
YouTube video / playlist, or a local mp3
        │  download + transcription
        ▼
work/sources/…/<date>_<model>_<version>.json ← source of truth (machine-produced, not edited)
        ├─► work/<title>_transcript.txt       ← readable view, for the chat (-c / -f)
        └─► ArchivTrace: import_sources.py    ← declared as a source of a research notebook
```

## The `yt2post-source/1` JSON

- `source_id`: `youtube:<video id>` (or `file:sha256:<content>` for a local mp3), never the
  title. A video in two playlists is one source: its `playlists` accumulate.
- `channel`: who published the video. No author is inferred: the channel, the speaker and
  the scientific author are often different people.
- `text_version`: fingerprint of the segments and of the transcription settings. Writing the
  same transcription again changes nothing; another model or other settings give a new file
  next to the previous one.
- File names are for people: the folder is `<Title>_<video_id>` (found again by the id if
  the title changes), the file `<date>_<model>_<first 6 characters of text_version>.json`.
  Programs identify a transcript by `source_id` and `text_version` inside the file.
- `segments`: `id`, `start`, `end` (seconds), `text`, in time order.
- The transcription is automatic: its fidelity to the audio is not established.
