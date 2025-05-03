# YouTube Video Transcription and Chatbot

This project provides a comprehensive tool for processing YouTube videos and engaging in AI-powered discussions about their content. It combines video downloading, audio transcription, and interactive AI chat capabilities using state-of-the-art open-source tools.

## Features

### Core Functionality
- Download audio from YouTube videos using `yt-dlp`
- Transcribe audio to text using OpenAI's `whisper` (or process a local .mp3 file directly)
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


2. **Install the required packages:**

   Make sure you have Python installed. Then run:

   ```bash
   pip install -r requirements.txt
   ```

3. **Additional Setup:**

   - Ensure `yt-dlp` is installed and accessible in your PATH.
   - Configure your `config.json` file with necessary parameters like `tmp_directory`, `work_directory`, and `model`.

4. **Ollama Setup:**

   Ollama must be installed and running on your local machine. To start Ollama, use:

   ```bash
   ollama serve &
   ollama run <model_version>
   ```

   The model version is defined in the `config.json` file under the `"model"` key.

## Usage

The tool provides several command-line options for different workflows:

### Basic Operations

```bash
# Transcribe a YouTube video
python yt2post.py -t <YouTube_URL>

# Transcribe a local mp3 file (no user prompts, metadata auto-extracted)
python yt2post.py -t /path/to/audio.mp3

# Chat about an existing transcript
python yt2post.py -c <transcript_file>

# Full process: download, transcribe, and chat
python yt2post.py -f <YouTube_URL>
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

### Basic Configuration
Create a `config.json` file in the root directory:

```json
{
    "tmp_directory": "path/to/tmp",
    "work_directory": "path/to/work",
    "model": "llama3.2"  // Default model, can be overridden with -m option
}
```

### Model Configuration
- The `model` in `config.json` specifies the default model
- Use the `-m` option to override this and select a model at runtime
- Available models can be listed using `ollama list`
- Running models can be viewed using `ollama ps`

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
│   ├── config_manager.py       # Configuration handling
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
- [Whisper](https://github.com/openai/whisper) for audio transcription.
- [Ollama](https://ollama.com/) for AI chatbot interactions.
