import subprocess
import os
import whisper
import argparse
import ollama

def download_audio(youtube_url):
    # Download the audio from the YouTube video
    result = subprocess.run(['yt-dlp', '-x', '--audio-format', 'mp3', '-o', '%(title)s.%(ext)s', '--verbose', youtube_url], capture_output=True, text=True)

    # Extract the audio file name from the output
    audio_file = None
    for line in result.stdout.split('\n'):
        if line.startswith('[ExtractAudio] Destination:'):
            audio_file = line.split(': ')[-1].strip()
            break

    if not audio_file:
        raise Exception("Unable to find the downloaded audio file")

    return audio_file

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
    return call_ia("Please extract the main ideas from the following text:", transcript_file)

def call_ia(prompt, transcript_file):
    # Open and read the content of the transcript file
    with open(transcript_file, 'r') as file:
        transcript_content = file.read()

    # Call Ollama to extract main ideas using the llama3.1 model
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
    
    parser.add_argument('url', help='URL of the YouTube video to download and process.')
    parser.add_argument('-d', '--download', help='Download the audio from a YouTube video URL', action='store_true')
    parser.add_argument('-t', '--transcribe', help='Transcrive the audio file to text.', action='store_true')
    parser.add_argument('-i', '--ideas', help='Get main ideas from the text', action='store_true')
    parser.add_argument('-l', '--linkedin', help='Generate linkedin post regarding ethics values from a text', action='store_true')
    parser.add_argument('-f', '--fullpost', help='Generate linkedin post from a youtube video URL', action='store_true')
    
    args = parser.parse_args()

    if args.download:
        print(f"download input is: {args.url}") 
        title = download_audio(args.url)
        print(f"Audio downloaded. Video title: {title}")

    elif args.transcribe:
        
        print(f"transcribe input is: {args.url}") 
        transcript_file = transcribe_audio(args.input)
        print(f"Audio transcribed. Transcript saved to: {transcript_file}")

    elif args.ideas:
        print(f"idea input is: {args.url}") 
        ideas = extract_main_ideas_from_transcript(args.input)
        print(f"Ideas extracted: {ideas}")

    elif args.linkedin:
        print(f"linkedin input is: {args.url}") 
        linkedin_post = create_linkedin_post(args.input)
        print(f"LinkedIn post created: {linkedin_post}")
        
    elif args.fullpost:
        print(f"fullpost input is: {args.url}") 
        linkedin_post = full_linkedin_post(args.url)
        print(f"LinkedIn post from youtube URL: {linkedin_post}")

if __name__ == '__main__':
    main()
