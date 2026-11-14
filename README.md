# YouTube Video Transcription and Chatbot

This project provides a comprehensive tool for processing YouTube videos and engaging in AI-powered discussions about their content. It combines video downloading, audio transcription, and interactive AI chat capabilities using state-of-the-art open-source tools.

## Features

### Core Functionality
- Download the audio of YouTube videos using `yt-dlp` (original language, small download)
- Transcribe audio to text using `faster-whisper` (or process a local .mp3 file directly)
- Use the GPU automatically when one works, the CPU otherwise
- Take the YouTube URL straight from the clipboard: copy the link, run one command
- Engage in interactive chat sessions about video content using `ollama` AI models

### Advanced Features
- Choice of the Ollama model among the installed ones (`-m`)
- Context size computed from the transcript, so the whole video fits in the chat
- Live progress with a pessimistic remaining time, and a detailed mode (`-v`)
- Everything runs on your computer: the transcript is only sent to your Ollama server

## Installation

### Windows: everything with winget

In PowerShell, install the tools (each command can be run again safely):

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id Gyan.FFmpeg.Essentials -e
winget install --id DenoLand.Deno -e
winget install --id Ollama.Ollama -e    # only for the chat options -c and -f
```

**Close and reopen PowerShell** (so the new commands are on the PATH), then:

```powershell
git clone https://github.com/fdepierre/YouTube2Post.git
cd YouTube2Post
python -m pip install -r requirements.txt
ollama pull qwen3.5:4b                  # only for the chat options -c and -f
python yt2post.py -t                    # transcribes the YouTube link copied in the browser
```

Python 3.12 is the version tested on Windows. Transcription runs on the CPU with the `base`
model, or on an NVIDIA GPU with `large-v3-turbo` after one more command (see
[Transcription Device](#transcription-device-cpu--gpu)).

### All systems

1. **Clone the repository:**

   ```bash
   git clone https://github.com/fdepierre/YouTube2Post.git
   cd YouTube2Post
   ```

2. **Install the required packages** (Python 3.10 or newer):

   ```bash
   pip install -r requirements.txt
   ```

3. **Install the external tools:**

   - [FFmpeg](https://ffmpeg.org/download.html), on your PATH.
   - A JavaScript runtime, needed by `yt-dlp` for YouTube: [Deno](https://deno.com)
     (recommended) or Node.js, on your PATH.

   On Windows, see the [winget commands](#windows-everything-with-winget) above.

4. **Optional, NVIDIA GPU:** see [Transcription Device](#transcription-device-cpu--gpu).

5. **Ollama** (only for the chat options `-c` and `-f`):

   [Install Ollama](https://ollama.com/download) (it runs as a background service) and
   download at least one model, for example:

   ```bash
   ollama pull qwen3.5:4b
   ```

   There is no need to start the model with `ollama run`: Ollama loads it on the first question.

## Usage

### Everyday use: copy the link, type `yt`

1. In the browser, copy the YouTube video link with `Ctrl+C`: on the video page press
   `Ctrl+L` then `Ctrl+C` (or use the Share button > Copy), or right-click a video
   thumbnail > *Copy link address*.
2. In the terminal, from any directory, type `yt` (see [the alias](#shortcut-a-yt-command)).
3. The program prints `Using YouTube URL from clipboard: ...`, downloads and transcribes the
   video, and ends with where the transcript was saved (see [Output](#output)); its full
   path is also copied to the clipboard.

With `-t` or `-f` and no URL, the program reads the YouTube URL from the clipboard
(Windows and WSL via PowerShell, macOS `pbpaste`, Linux `wl-paste`/`xclip`/`xsel`).
If the clipboard holds no YouTube URL, it asks for a URL or an mp3 file.

#### Shortcut: a `yt` command

Add an alias to `~/.bashrc` (Linux/WSL) or `~/.zshrc` (macOS), replacing the path with
your clone of the repository:

```bash
echo "alias yt='python /path/to/YouTube2Post/yt2post.py -t'" >> ~/.bashrc
source ~/.bashrc
```

If you use a conda environment, let the alias run in it, so you don't have to activate it
first (replace `myenv` with your environment name):

```bash
echo "alias yt='conda run --no-capture-output -n myenv python /path/to/YouTube2Post/yt2post.py -t'" >> ~/.bashrc
source ~/.bashrc
```

`yt` works from any directory: `config.json`, `tmp/` and `work/` are always taken from the
program's directory.

### Output

Each run shows its main steps numbered, then the result of each one:

```
[1/3] Loading the transcription model
  ✓ large-v3-turbo on CUDA (4s)

[2/3] Downloading the audio from YouTube https://youtu.be/...
  ✓ Video title, 7.1 MB (3s)

[3/3] Transcribing the audio
  Audio prepared in 0:07
  Transcribing 18:17 of audio (language: fr)...
  ✓ 18:17 of audio transcribed (fr) (26s)

Transcript saved to:
  Dir:  /path/to/YouTube2Post/work/
  File: Video_title_transcript.txt
  ✓ Full path copied to the clipboard
```

The full path of the transcript is copied to the clipboard, ready to paste, in the format
of where the program runs: `C:\Users\...` in PowerShell/cmd on Windows, `/mnt/c/Users/...`
in WSL (in the Windows clipboard, shared with Windows Terminal), `/home/...` on Linux or
macOS (`pbcopy`, `wl-copy`, `xclip` or `xsel`).

- While a step runs, a spinning line shows its progress: size, speed and remaining time
  while downloading (network retries are shown in yellow), position and remaining time
  while transcribing.
- `-v` / `--verbose` adds the technical details of each step, to understand or investigate:
  - the computer: OS and context (Windows, WSL, Linux), Python, CPU, RAM (in WSL, the VM's
    and the Windows host's), GPU with its memory, driver and temperature;
  - the load during each heavy step: CPU threads busy, GPU usage, memory peak and
    temperature (sampled with `nvidia-smi`, installed with the NVIDIA driver);
  - transcription: where the CPU/GPU choice comes from, model size, files and precision,
    detected language and confidence, speech kept after silence removal, speed;
  - download: yt-dlp's full log and the audio format;
  - chat: the Ollama server (version, address, where it runs: this computer, inside WSL or
    the Windows host), the API request sent (`think=false`, `num_ctx`), the GPU memory free
    for Ollama and the models already loaded, the model (parameters, quantization) and, after
    each answer, whether any reasoning was received, the tokens read and written, the speed,
    how much of the model is on the GPU or in RAM and until when Ollama keeps it loaded.
- Without `-v`, none of these measurements runs (no `nvidia-smi`, no extra Ollama request):
  the normal mode is not slowed down.
- Colours (step numbers, ✓, warnings in yellow, errors in red) and animations are used only
  in a terminal: redirected to a file, the output is plain text. Set the standard
  `NO_COLOR=1` environment variable to turn colours off.

### All options

```bash
# Transcribe the YouTube video whose URL is in the clipboard
python yt2post.py -t

# Transcribe a given YouTube video
python yt2post.py -t <YouTube_URL>

# Transcribe a local mp3 file (no user prompts, metadata auto-extracted)
python yt2post.py -t /path/to/audio.mp3

# Chat about an existing transcript (the file is required)
python yt2post.py -c <transcript_file>

# Full process: download, transcribe, and chat (URL from the clipboard if omitted)
python yt2post.py -f [<YouTube_URL>]

# Any of the above with the detailed log of each step
python yt2post.py -v -t <YouTube_URL>
```

### Model Selection

```bash
# Choose the Ollama model from the installed ones
python yt2post.py -m -c <transcript_file>
```

Without `-m`, the model is chosen automatically when there is no doubt: the model already
loaded in Ollama, or the only installed one. Otherwise, and always with `-m`, the installed
models are listed (▲ = already loaded) and you type a number; Enter takes the default (the
loaded model, else the most recently installed one).

Type `exit` during the chat to end the session.

## Configuration

The `config.json` file in the program's directory sets where files go:

```json
{
    "tmp_directory": "tmp",
    "work_directory": "work"
}
```

- `tmp_directory`: downloaded audio and metadata, emptied at each run. As a safety, the
  program refuses a directory whose emptying would delete other files: the work directory,
  the home directory, a drive root, or the program's directory.
- `work_directory`: the transcripts (`<video_title>_transcript.txt`, with the title reduced
  to letters, digits, `_` and `-`)

Relative paths are relative to the program's directory, wherever you start it from.
Absolute paths (or `~/...`) can be used to put the files elsewhere.

### Ollama Model
- See [Model Selection](#model-selection) for how the model is chosen
- The program uses the Ollama server set by the standard `OLLAMA_HOST` environment
  variable, by default `http://localhost:11434` (in WSL, this also reaches Ollama installed
  on Windows)
- Installed models can be listed using `ollama list`, loaded ones using `ollama ps`
- With `-f`, the Whisper model is freed from GPU memory before the chat starts
- The whole transcript is sent to the model: the context size (`num_ctx`) is computed from
  the transcript length (16k tokens for a ~45 min video), and the program prints it
- The hidden "thinking" of reasoning models (qwen3.5, gemma4...) is turned off: it made
  answers about 5x slower without better summaries
- Choose a model that fits in your GPU memory with that context (`ollama ps` should show
  `100% GPU`). E.g. on a 6 GB GPU, `qwen3.5:4b` runs fully on the GPU with 16k tokens of
  context, while 9B and larger models spill to the CPU and answer several times slower

### Transcription Device (CPU / GPU)
Transcription runs on the CPU by default, which works on any computer. On the first run,
the program tests once whether Faster Whisper can use a CUDA GPU (in a separate process,
so a broken CUDA setup cannot crash it) and remembers the result in
`~/.cache/yt2post/device.json`. The test runs again automatically on another computer or
Python environment, or after the CUDA libraries below are installed. If the GPU later fails
to start, the program falls back to the CPU.

The Whisper model depends on the device: `large-v3-turbo` on GPU (much more accurate,
~30 s for 18 min of audio, ~4 GB of GPU memory, 1.6 GB one-time download) and `base` on
CPU (fast on any computer). If a GPU transcription fails (e.g. not enough GPU memory),
it is retried on the CPU with `base`.

To use an NVIDIA GPU, install the CUDA 12 libraries used by faster-whisper (~1 GB):

In PowerShell on Windows, or in a shell on Linux / WSL (the same `python` that runs yt2post):

```bash
python -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

Nothing else to set up (no PATH or `LD_LIBRARY_PATH`): the program loads them from where pip
installed them (Python's site-packages directories only, never the current directory). The
next run tests the GPU again automatically.

- Force a device: `YT2POST_DEVICE=cpu python yt2post.py ...` (or `cuda`)
- Re-run the test: delete `~/.cache/yt2post/device.json`

## Security and Privacy

- **Local processing:** the audio is transcribed on your computer, and the transcript is
  only sent to your Ollama server (local by default, see `OLLAMA_HOST`).
- **Network:** the program contacts YouTube (through `yt-dlp`, with TLS certificates checked)
  and, the first time, Hugging Face to download the Whisper model. YouTube's player script is
  run in Deno/Node to solve its challenges, as `yt-dlp` requires; the solver comes from the
  `yt-dlp-ejs` package installed by pip, nothing is downloaded from GitHub at run time.
- **Commands:** external tools (`clip.exe`, `xclip`, `nvidia-smi`, `powershell.exe`...) are
  run without a shell, with fixed arguments: a video title or URL cannot inject a command.
- **Files:** the transcript file name is made from the video title reduced to safe characters,
  so a title cannot write outside the work directory; the temporary directory is checked before
  being emptied (see [Configuration](#configuration)).
- **The chat model reads untrusted text:** a video's transcript or description could contain
  instructions aimed at the model (prompt injection). The model has no tools or access to your
  files, so this can only affect its answers: keep a critical eye on them.
- **Dependencies** are installed with minimum versions (`>=`), to get security fixes; update
  them from time to time with `pip install -U -r requirements.txt`.

## Development

### Testing

```bash
# Run all tests (a few use the network, YouTube, the GPU or Ollama: the Ollama tests are
# skipped when it is not running)
pytest

# Run tests with coverage report
pytest --cov=modules tests/

# Generate HTML coverage report
pytest --cov=modules --cov-report=html tests/
```

View the coverage report at `htmlcov/index.html`

### Project Structure

```
YouTube2Post/
├── modules/                    # Core functionality modules
│   ├── clipboard.py            # Read the YouTube URL from the clipboard
│   ├── config_manager.py       # Configuration handling
│   ├── device_selector.py      # CPU/GPU detection for transcription
│   ├── directory_manager.py    # File and directory management
│   ├── ollama_manager.py       # AI model interaction
│   ├── progress.py             # Spinner and live progress line
│   ├── sysinfo.py              # Hardware and load details (verbose mode)
│   ├── transcriber.py          # Audio transcription
│   ├── ui.py                   # Colours and numbered steps
│   └── youtube_downloader.py   # YouTube video processing
├── tests/                      # Test suite
├── config.json                 # Configuration file
├── requirements.txt            # Python dependencies
└── yt2post.py                  # Main script
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

Ensure your code follows the project's style and passes all tests.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for downloading YouTube content.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and [Whisper](https://github.com/openai/whisper) for audio transcription.
- [Ollama](https://ollama.com/) for AI chatbot interactions.
