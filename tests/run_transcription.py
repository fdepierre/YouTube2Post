import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

from transcriber import Transcriber

def main():
    # Initialize transcriber
    transcriber = Transcriber(work_directory='.')
    
    # Transcribe the audio file
    transcript_file = transcriber.transcribe_audio('test_transcriber.mp3')
    print(f"Transcription completed. Output saved to: {transcript_file}")

if __name__ == '__main__':
    main()
