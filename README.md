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
- Runtime model selection from available or running Ollama models
- Smart handling of model availability and startup
- Robust error handling and graceful session management
- Support for multiple exit commands and interrupt handling

## Installation

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

4. **Optional, NVIDIA GPU:** see [Transcription Device](#transcription-device-cpu--gpu).

5. **Ollama** (only for the chat options `-c` and `-f`):

   Ollama must be installed and running on your local machine, with a model started:

   ```bash
   ollama serve &
   ollama run <model_name>
   ```

   The program uses the running model (or lets you choose with `-m`).

## Usage

### Everyday use: copy the link, type `yt`

1. In the browser, copy the YouTube video link with `Ctrl+C`: on the video page press
   `Ctrl+L` then `Ctrl+C` (or use the Share button > Copy), or right-click a video
   thumbnail > *Copy link address*.
2. In the terminal, from any directory, type `yt` (see [the alias](#shortcut-a-yt-command)).
3. The program prints `Using YouTube URL from clipboard: ...`, downloads and transcribes the
   video, and ends with the full path of the transcript, e.g.
   `Transcript saved to: /home/me/YouTube2Post/work/My_video_title_transcript.txt`

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

### All options

```bash
# Transcribe the YouTube video whose URL is in the clipboard
python yt2post.py -t

# Transcribe a given YouTube video
python yt2post.py -t <YouTube_URL>

# Transcribe a local mp3 file (no user prompts, metadata auto-extracted)
python yt2post.py -t /path/to/audio.mp3

# Chat about an existing transcript
python yt2post.py -c <transcript_file>

# Full process: download, transcribe, and chat (URL from the clipboard if omitted)
python yt2post.py -f [<YouTube_URL>]
```

### Model Selection

```bash
# Use model selection interface
python yt2post.py -m -c <transcript_file>
```

When using the `-m` option:
- If models are running, you can select one directly
- If no models are running, available models will be listed
- Press Enter to use a single running model, or type 'no' to see alternatives
- Type 'exit' during chat to end the session

## Configuration

The `config.json` file in the program's directory sets where files go:

```json
{
    "tmp_directory": "tmp",
    "work_directory": "work"
}
```

- `tmp_directory`: downloaded audio and metadata, emptied at each run
- `work_directory`: the transcripts (`<video_title>_transcript.txt`)

Relative paths are relative to the program's directory, wherever you start it from.
Absolute paths (or `~/...`) can be used to put the files elsewhere.

### Ollama Model
- By default, the currently running Ollama model is used
- Use the `-m` option to select a model at runtime
- Available models can be listed using `ollama list`
- Running models can be viewed using `ollama ps`

### Transcription Device (CPU / GPU)
Transcription runs on the CPU by default, which works on any computer. On the first run,
the program tests once whether Faster Whisper can use a CUDA GPU (in a separate process,
so a broken CUDA setup cannot crash it) and remembers the result in
`~/.cache/yt2post/device.json`. The test runs again automatically on another computer or
Python environment. If the GPU later fails to start, the program falls back to the CPU.

The Whisper model depends on the device: `large-v3-turbo` on GPU (much more accurate,
~30 s for 18 min of audio, ~4 GB of GPU memory, 1.6 GB one-time download) and `base` on
CPU (fast on any computer). If a GPU transcription fails (e.g. not enough GPU memory),
it is retried on the CPU with `base`.

To use an NVIDIA GPU, install the CUDA 12 libraries used by faster-whisper and, on Linux/WSL,
make them findable (put the `export` line in `~/.bashrc`, or for a conda environment use
`conda env config vars set LD_LIBRARY_PATH=...`):

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
export LD_LIBRARY_PATH=$(python -c 'import nvidia.cublas.lib as b, nvidia.cudnn.lib as d; print(b.__path__[0] + ":" + d.__path__[0])')
```

Then delete `~/.cache/yt2post/device.json` so the GPU test runs again.

- Force a device: `YT2POST_DEVICE=cpu python yt2post.py ...` (or `cuda`)
- Re-run the test: delete `~/.cache/yt2post/device.json`

## Development

### Testing and Quality Assurance

The project maintains high code quality through comprehensive testing:

```bash
# Run all tests
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
│   ├── transcriber.py          # Audio transcription
│   └── youtube_downloader.py   # YouTube video processing
├── tests/                      # Test suite
├── config.json                # Configuration file
├── requirements.txt           # Python dependencies
└── yt2post.py                # Main script
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

Ensure your code follows the project's style and passes all tests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for downloading YouTube content.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and [Whisper](https://github.com/openai/whisper) for audio transcription.
- [Ollama](https://ollama.com/) for AI chatbot interactions.
