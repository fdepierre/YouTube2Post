import argparse
import sys

from modules.config_manager import ConfigManager
from modules.directory_manager import DirectoryManager
from modules.youtube_downloader import YouTubeDownloader
from modules.transcriber import Transcriber
from modules.chatbot import Chatbot

def main():
    parser = argparse.ArgumentParser(description='Process YouTube videos and interact with AI.')
    parser.add_argument('-t', '--transcribe', help='Download and transcribe the YouTube video', action='store_true')
    parser.add_argument('-c', '--chat', help='Chat with AI based on the transcript.', action='store_true')
    parser.add_argument('-f', '--full', help='Download, transcribe, and chat with AI.', action='store_true')
    parser.add_argument('url_or_input', help='URL of the YouTube video or input file (mp3 or text) for processing.', nargs='?')

    args = parser.parse_args()

    try:
        config_manager = ConfigManager()
        tmp_dir = config_manager.read_config('tmp_directory')
        work_dir = config_manager.read_config('work_directory')
        model_name = config_manager.read_config('model')

        directory_manager = DirectoryManager(tmp_directory=tmp_dir, work_directory=work_dir)
        
        try:
            youtube_downloader = YouTubeDownloader(tmp_directory=tmp_dir)
        except (ImportError, RuntimeError) as e:
            print(f"\nDependency Error: {str(e)}")
            sys.exit(1)
            
        transcriber = Transcriber(work_directory=work_dir)
        chatbot = Chatbot(model=model_name)

        # Check if no mutually exclusive argument is provided
        if not (args.transcribe or args.chat or args.full):
            parser.print_help()
            sys.exit(1) 
        
        elif args.transcribe:
            try:
                audio_file, json_file = youtube_downloader.download_audio(args.url_or_input)
                transcript_file = transcriber.create_transcript_content(audio_file, json_file, args.url_or_input)
                print(f"Transcript saved to: {transcript_file}")
            except Exception as e:
                print(f"\nError during transcription process: {str(e)}")
                sys.exit(1)

        elif args.chat:
            try:
                chatbot.interactive_chat(args.url_or_input)
            except Exception as e:
                print(f"\nError during chat process: {str(e)}")
                sys.exit(1)

        elif args.full:
            try:
                audio_file, json_file = youtube_downloader.download_audio(args.url_or_input)
                transcript_file = transcriber.create_transcript_content(audio_file, json_file, args.url_or_input)
                chatbot.interactive_chat(transcript_file)
            except Exception as e:
                print(f"\nError during full process: {str(e)}")
                sys.exit(1)

    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
