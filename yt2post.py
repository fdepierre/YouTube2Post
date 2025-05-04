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
    python yt2post.py [-t|--transcribe] [-c|--chat] [-f|--full] <youtube_url_or_mp3_file>

Arguments:
    <youtube_url_or_mp3_file>   URL of the YouTube video or path to a local .mp3 file to process.

Notes:
- Only local .mp3 files are supported for direct audio transcription (other formats must be converted to mp3 first).
- Metadata (title, author, description) is automatically extracted from the mp3 if present, or defaults are used.
"""

import argparse
import sys
import os
import argcomplete

from modules.config_manager import ConfigManager
from modules.directory_manager import DirectoryManager
from modules.youtube_downloader import YouTubeDownloader
from modules.transcriber import Transcriber
from modules.ollama_manager import OllamaManager



def main():
    # Initialize argument parser with program description
    parser = argparse.ArgumentParser(
    description='Process YouTube videos (via URL) or local .mp3 files: download, transcribe, and chat with AI.\n'
                'Input can be a YouTube URL or a path to a local .mp3 file. Only .mp3 is supported for local audio.'
)
    parser.add_argument('-t', '--transcribe', help='Download and transcribe the YouTube video or local mp3 file', action='store_true')
    parser.add_argument('-c', '--chat', help='Chat with AI based on the transcript.', action='store_true')
    parser.add_argument('-f', '--full', help='Download, transcribe, and chat with AI.', action='store_true')
    parser.add_argument('-m', '--model-select', help='Select a specific Ollama model (overrides default: use the currently running model)', action='store_true')
    parser.add_argument('url_or_input', help='URL of the YouTube video or input file (mp3 or text) for processing.', nargs='?')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    try:
        # Initialize configuration and required components
        config_manager = ConfigManager()
        tmp_dir = config_manager.read_config('tmp_directory')
        work_dir = config_manager.read_config('work_directory')
        directory_manager = DirectoryManager(tmp_directory=tmp_dir, work_directory=work_dir)
        
        # Initialize YouTube downloader with error handling
        try:
            youtube_downloader = YouTubeDownloader(tmp_directory=tmp_dir)
        except (ImportError, RuntimeError) as e:
            print(f"\nDependency Error: {str(e)}")
            sys.exit(1)

        model_name = None
        chat_manager = None
        # Only initialize Ollama and select model if chat or full mode is required
        if args.chat or args.full:
            ollama_manager = OllamaManager()
            try:
                running_models = ollama_manager.list_running_models()
                available_models = ollama_manager.list_available_models()
                # If -m is used, prompt user to select from running models, or check if requested model is running
                if args.model_select:
                    if not running_models:
                        print("\nNo models are currently running. Available models:")
                        for model in available_models:
                            print(f"- {model}")
                        print("\nPlease start one of these models using 'ollama run <model_name>' and try again.")
                        sys.exit(1)
                    print("\nInteractive model selection:")
                    model_name = ollama_manager.select_model(use_running=True)
                else:
                    if not running_models:
                        print("\nNo models are currently running. Available models:")
                        for model in available_models:
                            print(f"- {model}")
                        print("\nPlease start one of these models using 'ollama run <model_name>' and try again.")
                        sys.exit(1)
                    elif len(running_models) == 1:
                        model_name = running_models[0]
                        print(f"\nOnly one model is running: '{model_name}' will be used.")
                    else:
                        print("\nMultiple models are running:")
                        model_name = ollama_manager.select_model(use_running=True)
                        print(f"Selected model: {model_name}")
                chat_manager = OllamaManager(model=model_name)
            except Exception as e:
                print(str(e))
                sys.exit(1)

        # Validate command-line arguments
        if not (args.transcribe or args.chat or args.full):
            parser.print_help()
            sys.exit(1) 
        
        # Handle transcription-only mode
        elif args.transcribe:
            try:
                transcriber = Transcriber(work_directory=work_dir)
                input_path = args.url_or_input
                if input_path and input_path.lower().endswith('.mp3') and os.path.isfile(input_path):
                    # Use local mp3 file and generate minimal metadata JSON
                    import json
                    base = os.path.splitext(os.path.basename(input_path))[0]
                    json_file = os.path.join(tmp_dir, f"{base}.info.json")
                    if not os.path.exists(json_file):
                        # Extract metadata from mp3 using mutagen
                        try:
                            from mutagen.easyid3 import EasyID3
                            audio = EasyID3(input_path)
                            title = audio.get('title', [base])[0]
                            author = audio.get('artist', ['Unknown'])[0]
                            description = audio.get('comment', [''])[0]
                        except Exception:
                            title = base
                            author = "Unknown"
                            description = ""
                        meta = {"title": title, "author": author, "description": description}
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(meta, f)
                    audio_file = input_path
                    youtube_url = input_path  # For transcript content, just pass the file path
                else:
                    audio_file, json_file = youtube_downloader.download_audio(input_path)
                    youtube_url = input_path
                transcript_file = transcriber.create_transcript_content(audio_file, json_file, youtube_url)
                print(f"Transcript saved to: {transcript_file}")
            except Exception as e:
                print(f"\nError during transcription process: {str(e)}")
                sys.exit(1)

        # Handle chat-only mode
        elif args.chat:
            try:
                chat_manager.interactive_chat(args.url_or_input)
            except Exception as e:
                print(f"\nError during chat process: {str(e)}")
                sys.exit(1)

        # Handle full process mode (download, transcribe, and chat)
        elif args.full:
            try:
                transcriber = Transcriber(work_directory=work_dir)
                input_path = args.url_or_input
                if input_path and input_path.lower().endswith('.mp3') and os.path.isfile(input_path):
                    # Use local mp3 file and generate minimal metadata JSON
                    import json
                    base = os.path.splitext(os.path.basename(input_path))[0]
                    json_file = os.path.join(tmp_dir, f"{base}.info.json")
                    if not os.path.exists(json_file):
                        # Extract metadata from mp3 using mutagen
                        try:
                            from mutagen.easyid3 import EasyID3
                            audio = EasyID3(input_path)
                            title = audio.get('title', [base])[0]
                            author = audio.get('artist', ['Unknown'])[0]
                            description = audio.get('comment', [''])[0]
                        except Exception:
                            title = base
                            author = "Unknown"
                            description = ""
                        meta = {"title": title, "author": author, "description": description}
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(meta, f)
                    audio_file = input_path
                    youtube_url = input_path  # For transcript content, just pass the file path
                else:
                    audio_file, json_file = youtube_downloader.download_audio(input_path)
                    youtube_url = input_path
                transcript_file = transcriber.create_transcript_content(audio_file, json_file, youtube_url)
                chat_manager.interactive_chat(transcript_file)
            except Exception as e:
                print(f"\nError during full process: {str(e)}")
                sys.exit(1)

    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
