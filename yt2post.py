import subprocess
import os
import whisper
import argparse
import ollama
import re
import sys



def download_audio(youtube_url):
    # Specify the directory to save the audio files
    save_directory = 'work'
    os.makedirs(save_directory, exist_ok=True)  # Create directory if it doesn't exist
    
    # Download the audio from the YouTube video with overwrite option
    result = subprocess.run(
        ['yt-dlp', '-x', '--audio-format', 'mp3', '--force-overwrites',
         '-o', f'{save_directory}/%(title)s.%(ext)s', '--verbose', youtube_url], 
        capture_output=True, text=True)
    
    # Extract the audio file name from the output
    audio_file = None
    for line in result.stdout.split('\n'):
        if line.startswith('[ExtractAudio] Destination:'):
            audio_file = line.split(': ')[-1].strip()
            break
    
    if not audio_file:
        raise Exception(f"Unable to find the downloaded audio file in directory: {os.path.abspath(save_directory)}")
    
    # Simplify the filename
    simple_name = re.sub(r'\W+', '_', os.path.splitext(os.path.basename(audio_file))[0])  # Replace non-alphanumeric characters with underscores
    simple_name = simple_name[:50]  # Optionally limit length to 50 characters
    simple_audio_file = f"{save_directory}/{simple_name}.mp3"
    
    # Rename the file if necessary (only if names differ)
    if audio_file != simple_audio_file:
        os.rename(audio_file, simple_audio_file)
    
    return simple_audio_file

def transcribe_audio(audio_file):
    # Load the Whisper model
    model = whisper.load_model("base")
    
    # Transcribe the audio file
    result = model.transcribe(audio_file)
 
    # Save the transcription to a text file
    with open(f"{audio_file}.txt", "w") as f:
        f.write(result['text'])
        
    return f"{audio_file}.txt"

def extract_main_ideas_from_transcript(transcript_file):
    # Read the transcript file and extract main ideas using AI
    return call_ia("Please extract the main ideas from the following Youtube video transcript:", transcript_file)


def check_ollama_running():
    try:
        # Attempt a simple chat interaction to see if Ollama is responsive
        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'user', 'content': 'Hello'}
            ]
        )
        # Check if the response contains expected data
        return 'message' in response and 'content' in response['message']
    except Exception as e:
        # If an exception occurs, Ollama is likely not running
        print(f"Error checking Ollama: {e}")
        return False

def call_ia(prompt, transcript_file):
    # Check if Ollama is running
    if not check_ollama_running():
        raise Exception('Ollama service is not running. Please start Ollama.')

    # Open and read the content of the transcript file
    with open(transcript_file, 'r') as file:
        transcript_content = file.read()

    # Call Ollama to extract main ideas using the llama3.2 model
    response = ollama.chat(
        model='llama3.2',
        messages=[
            {'role': 'user', 'content': f'{prompt} {transcript_content}'}
        ]
    )

    # Extract and return the main ideas from the response
    main_ideas = response['message']['content']
    return main_ideas


def create_linkedin_post(transcript_file):
    # Prompt for creating a LinkedIn post based on the transcript
    pre_prompt = "Create a LinkedIn post (maximum 1000 characters) expressing appreciation for this video. Highlight its importance in understanding our society's future. Emphasize aspects that demonstrate a move towards modernity, human equality, respect for nature, and a low-carbon society."
    
    return call_ia(pre_prompt, transcript_file)

def full_linkedin_post(youtube_url):
    # Execute full process: download, transcribe, and create a LinkedIn post
    audio_file = download_audio(youtube_url)
    transcript_file = transcribe_audio(audio_file)
    
    linkedin_post = create_linkedin_post(transcript_file)
    
    return linkedin_post
 

def main():
    # Set up argument parser for command-line interface
    parser = argparse.ArgumentParser(description='Transcribe YouTube content and create your post')

    # Create mutually exclusive group
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--download', help='Download the audio from a YouTube video URL', action='store_true')
    group.add_argument('-t', '--transcribe', help='Transcribe the audio file to text.', action='store_true')
    group.add_argument('-i', '--ideas', help='Get main ideas from the text', action='store_true')
    group.add_argument('-l', '--linkedin', help='Generate LinkedIn post regarding ethics values from a text', action='store_true')
    group.add_argument('-f', '--fullpost', help='Generate LinkedIn post from a YouTube video URL', action='store_true')

    # Arguments for URL and input file
    parser.add_argument('url_or_input', help='URL of the YouTube video or input file (mp3 or text) for processing.', nargs='?')

    args = parser.parse_args()

    # Check if no mutually exclusive argument is provided
    if not (args.download or args.transcribe or args.ideas or args.linkedin or args.fullpost):
        parser.print_help()
        sys.exit(1)

    if args.download:
        print(f"download input is: {args.url_or_input}") 
        title = download_audio(args.url_or_input)
        print(f"Audio downloaded. Video title: {title}")

    elif args.transcribe:
        print(f"transcribe input is: {args.url_or_input}") 
        transcript_file = transcribe_audio(args.url_or_input)
        print(f"Audio transcribed. Transcript saved to: {transcript_file}")

    elif args.ideas:
        print(f"idea input is: {args.url_or_input}") 
        ideas = extract_main_ideas_from_transcript(args.url_or_input)
        print(f"Ideas extracted: {ideas}")

    elif args.linkedin:
        print(f"linkedin input is: {args.url_or_input}") 
        linkedin_post = create_linkedin_post(args.url_or_input)
        print(f"LinkedIn post created: {linkedin_post}")
        
    elif args.fullpost:
        print(f"fullpost input is: {args.url_or_input}") 
        linkedin_post = full_linkedin_post(args.url_or_input)
        print(f"LinkedIn post from youtube URL: {linkedin_post}")

if __name__ == '__main__':
    main()

