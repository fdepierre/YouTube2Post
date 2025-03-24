#!/usr/bin/env python3
"""
YouTube to Post Converter
------------------------
This script downloads YouTube videos, transcribes them, and enables AI-powered chat interactions
based on the video content. It supports three main operations:
- Transcription only: Downloads and transcribes a YouTube video
- Chat only: Initiates a chat session based on an existing transcript
- Full process: Combines both operations (download, transcribe, and chat)

Usage:
    python yt2post.py [-t|--transcribe] [-c|--chat] [-f|--full] <youtube_url_or_input_file>
"""

import argparse
import sys
import argcomplete

from modules.config_manager import ConfigManager
from modules.directory_manager import DirectoryManager
from modules.youtube_downloader import YouTubeDownloader
from modules.transcriber import Transcriber
from modules.ollama_manager import OllamaManager



def main():
    # Initialize argument parser with program description
    parser = argparse.ArgumentParser(description='Process YouTube videos and interact with AI.')
    parser.add_argument('-t', '--transcribe', help='Download and transcribe the YouTube video', action='store_true')
    parser.add_argument('-c', '--chat', help='Chat with AI based on the transcript.', action='store_true')
    parser.add_argument('-f', '--full', help='Download, transcribe, and chat with AI.', action='store_true')
    parser.add_argument('-m', '--model-select', help='Select from running models', action='store_true')
    parser.add_argument('url_or_input', help='URL of the YouTube video or input file (mp3 or text) for processing.', nargs='?')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    try:
        # Initialize configuration and required components
        config_manager = ConfigManager()
        tmp_dir = config_manager.read_config('tmp_directory')
        work_dir = config_manager.read_config('work_directory')
        directory_manager = DirectoryManager(tmp_directory=tmp_dir, work_directory=work_dir)
        
        # Handle model selection
        ollama_manager = OllamaManager()
        
        try:
            if args.model_select:
                # Interactive mode with model selection
                model_name = ollama_manager.select_model(use_running=True)
            else:
                # Non-interactive mode: auto-select first running model
                model_name = ollama_manager.select_model(use_running=True, non_interactive=True)
        except Exception as e:
            print(str(e))
            sys.exit(1)
        
        # Initialize YouTube downloader with error handling
        try:
            youtube_downloader = YouTubeDownloader(tmp_directory=tmp_dir)
        except (ImportError, RuntimeError) as e:
            print(f"\nDependency Error: {str(e)}")
            sys.exit(1)
            
        chat_manager = OllamaManager(model=model_name)

        # Validate command-line arguments
        if not (args.transcribe or args.chat or args.full):
            parser.print_help()
            sys.exit(1) 
        
        # Handle transcription-only mode
        elif args.transcribe:
            try:
                transcriber = Transcriber(work_directory=work_dir)
                audio_file, json_file = youtube_downloader.download_audio(args.url_or_input)
                transcript_file = transcriber.create_transcript_content(audio_file, json_file, args.url_or_input)
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
                audio_file, json_file = youtube_downloader.download_audio(args.url_or_input)
                transcript_file = transcriber.create_transcript_content(audio_file, json_file, args.url_or_input)
                chat_manager.interactive_chat(transcript_file)
            except Exception as e:
                print(f"\nError during full process: {str(e)}")
                sys.exit(1)

    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
