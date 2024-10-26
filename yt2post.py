import subprocess
import os
import whisper
import argparse
import ollama
import re
import sys
import json


class ConfigError(Exception):
    pass

def read_config(parameter):
    
    config_file_path = 'config.json'
     
    try:
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        raise ConfigError(f"Config file '{config_file_path}' not found.")
    
    if parameter is not None:
        if parameter not in config:
            raise ConfigError(f"Parameter '{parameter}' not found in configuration.")
        tmp = config[parameter]
        return tmp
    
    raise ConfigError("No parameter specified.")

def create_working_dir():
    
    try:
        tmp_directory = read_config('tmp_directory')
        work_directory = read_config('work_directory')
    except ConfigError as e:
        print(e)

    os.makedirs(tmp_directory, exist_ok=True)
    os.makedirs(work_directory, exist_ok=True)

    # Clear tmp directory
    for file in os.listdir(tmp_directory):
        file_path = os.path.join(tmp_directory, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            
    return tmp_directory, work_directory

def download_audio(youtube_url):
    
    tmp_directory, work_directory = create_working_dir()
    
    # Download audio and metadata
    result = subprocess.run(
        ['yt-dlp', '-x', '--audio-format', 'mp3', '--write-info-json',
         '-o', f'{tmp_directory}/%(title)s.%(ext)s', youtube_url],
        check=True
    )
    
    # Find downloaded files
    for file in os.listdir(tmp_directory):
        if file.endswith('.mp3'):
            audio_file = os.path.join(tmp_directory, file)
        elif file.endswith('.json'):
            json_file = os.path.join(tmp_directory, file)

    return audio_file, json_file

def transcribe_audio(audio_file):
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    
    transcript_file = f"{audio_file}.txt"
    with open(transcript_file, "w") as f:
        f.write(result['text'])
        
    return transcript_file

def extract_metadata(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    title = data.get('title', 'Unknown Title')
    author = data.get('uploader', 'Unknown Author')
    description = data.get('description', 'No Description')
    
    return title, author, description

def create_transcript_content(youtube_url):
    
    audio_file, json_file = download_audio(youtube_url)
     
    title, author, description = extract_metadata(json_file)
    
    transcript_file = transcribe_audio(audio_file)
    
    with open(transcript_file, 'r') as f:
        transcript_content = f.read()
    
    full_content = (
        f"The following YouTube transcript is \"{title}\" from {youtube_url}\n"
        f"The author is: {author}\n"
        f"The video description is: {description}\n\n"
        "The following text is the transcript of the video:\n"
        f"{transcript_content}"
    )
    
    try:
        work_directory = read_config('work_directory')
    except ConfigError as e:
        print(e)
    
    full_content_file = os.path.join(f"{work_directory}/{title}_summary.txt")
    
    with open(full_content_file, 'w') as f:
        f.write(full_content)
    
    return full_content_file
 
def check_ollama_running(model):
    try:
        # Attempt a simple chat interaction to see if Ollama is responsive
        response = ollama.chat(
            model=model,
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

def call_ia(prompt, transcript_file, model):
    
    # Check if Ollama is running
    if not check_ollama_running(model):
        raise Exception('Ollama service is not running. Please start Ollama.')

    # Open and read the content of the transcript file
    with open(transcript_file, 'r') as file:
        transcript_content = file.read()

    # Call Ollama to extract main ideas using the llama3.2 model
    response = ollama.chat(
        model=model,
        messages=[
            {'role': 'user', 'content': f'{prompt} {transcript_content}'}
        ]
    )

    # Extract and return the main ideas from the response
    main_ideas = response['message']['content']
    return main_ideas

# Interactive chat function with history
def interactive_chat_with_history(transcript_file, model):

    print('transcript_file: '+transcript_file)

    # Check if Ollama is running
    if not check_ollama_running(model):
        raise Exception('Ollama service is not running. Please start Ollama.')

    chat_history = []

    # Read the transcript file and add it to the history
    with open(transcript_file, 'r') as file:
        transcript_content = file.read()
        chat_history.append({'role': 'system', 'content': transcript_content})

    print("Type 'exit' to end the chat.")

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Chatbot: Goodbye!")
            break

        # Add user's message to the history
        chat_history.append({'role': 'user', 'content': user_input})

        # Send request to the AI with the entire history
        response = ollama.chat(
            model=model,
            messages=chat_history
        )

        ai_response = response['message']['content']
        print("Chatbot:", ai_response)

        # Add AI's response to the history
        chat_history.append({'role': 'assistant', 'content': ai_response})


def talk_2youtube_video(youtube_url, model):
    # Execute full process: download, transcribe, and create a LinkedIn post
    
    full_content_file = create_transcript_content(youtube_url)
     
    full_chat = interactive_chat_with_history(full_content_file, model) 
    
    return full_chat
 

def main():
    # Set up argument parser for command-line interface
    parser = argparse.ArgumentParser(description='Transcribe YouTube content and create your post')

    # Create mutually exclusive group
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-t', '--transcribe', help='Download and transcribe the youtube video', action='store_true')
    group.add_argument('-c', '--chat', help='Chat with AI based on the transcript.', action='store_true')
    group.add_argument('-f', '--full', help='Download, transcrit and Chat with AI.', action='store_true')

    # Arguments for URL and input file
    parser.add_argument('url_or_input', help='URL of the YouTube video or input file (mp3 or text) for processing.', nargs='?')

    args = parser.parse_args() 
    
    try:
        model = read_config('model')
    except ConfigError as e:
        print(e)
    
    # Check if no mutually exclusive argument is provided
    if not (args.transcribe or args.chat or args.full):
        parser.print_help()
        sys.exit(1)

    if args.transcribe:
        print(f"transcribe input is: {args.url_or_input}") 
        transcript_file = create_transcript_content(args.url_or_input)
        print(f"Audio transcribed. Transcript saved to: {transcript_file}")

    elif args.chat:
        print(f"chat input is: {args.url_or_input}") 
        chat = interactive_chat_with_history(args.url_or_input, model)
        print(f"Your chat: {chat}")   
    
    elif args.full:
        print(f"Full talk input is: {args.url_or_input}") 
        chat = talk_2youtube_video(args.url_or_input, model)
        print(f"You full chat: {chat}")


if __name__ == '__main__':
    main()

