# YouTube Video Transcription and Chatbot

This project provides a tool to download, transcribe YouTube videos, and interact with an AI chatbot based on the transcriptions. It leverages `yt-dlp` for downloading audio, `whisper` for transcription, and `ollama` for AI interactions.

## Features

- Download audio from YouTube videos.
- Transcribe audio to text using Whisper.
- Engage in interactive chat sessions with AI based on video transcripts.

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/fdepierre/YouTube2Post.git
   cd yourproject


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

You can use this tool via command-line interface:

- **Transcribe a YouTube video:**

  ```bash
  python yt2post.py -t <YouTube_URL>
  ```

- **Chat based on a transcript file:**

  ```bash
  python yt2post.py -c <transcript_file>
  ```

- **Full process (download, transcribe, chat):**

  ```bash
  python yt2post.py -f <YouTube_URL>
  ```

## Configuration

Ensure you have a `config.json` file in the root directory with the following structure:

```json
{
    "tmp_directory": "path/to/tmp",
    "work_directory": "path/to/work",
    "model": "llama3.2"
}
```

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for downloading YouTube content.
- [Whisper](https://github.com/openai/whisper) for audio transcription.
- [Ollama](https://ollama.com/) for AI chatbot interactions.

```

This version includes instructions for setting up and running Ollama on your local machine, ensuring users understand how to start the service and use the specified model version from the configuration file.
