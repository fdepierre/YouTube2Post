"""
Chatbot Module
-------------
This module implements an interactive chatbot using the Ollama API.
It provides functionality to have conversations with an AI model about
the content of video transcripts.
"""

import ollama

class Chatbot:
    """
    A class to handle interactive chat sessions using Ollama models.
    
    This class provides methods to interact with Ollama AI models,
    enabling conversations about video transcript content. It includes
    service availability checking and interactive chat functionality.
    
    Attributes:
        model (str): Name of the Ollama model to use for chat
    """

    def __init__(self, model):
        """
        Initialize the Chatbot with a specific Ollama model.
        
        Args:
            model (str): Name of the Ollama model to use (e.g., 'deepseek-r1')
        """
        self.model = model

    def check_ollama_running(self):
        """
        Check if the Ollama service is running and the model is available.
        
        This method attempts to send a test message to verify both service
        availability and model existence.
        
        Returns:
            bool: True if Ollama is running and model is available, False otherwise
            
        Raises:
            Exception: If the specified model is not available in Ollama
        """
        try:
            # Check if Ollama service is running
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': 'Hello'}]
            )
            
            # Verify response format
            if not ('message' in response and 'content' in response['message']):
                return False
                
            return True

        except Exception as e:
            if "no such model" in str(e).lower():
                raise Exception(f"Model {self.model} is not available. Please check your config.json and make sure it matches an available Ollama model.")
            return False

    def interactive_chat(self, transcript_file):
        """
        Start an interactive chat session about a video transcript.
        
        This method initiates a chat session where users can ask questions
        about the content of a video transcript. The session continues until
        the user types 'exit'.
        
        Args:
            transcript_file (str): Path to the transcript file to discuss
            
        Raises:
            Exception: If Ollama service is not running
        """
        if not self.check_ollama_running():
            raise Exception('Ollama service is not running. Please start Ollama.')
        
        # Open and read the content of the transcript file
        with open(transcript_file, 'r') as file:
            transcript_content = file.read()

        # Initialize chat history with transcript as system context
        chat_history = [{'role': 'system', 'content': transcript_content}]
        
        # Start interactive chat loop
        while True:
            user_input = input("User: ")
            if user_input.lower() == "exit":
                print("Chatbot: Goodbye!")
                break
            
            # Add user message to chat history
            chat_history.append({'role': 'user', 'content': user_input})
            
            # Get AI response
            response = ollama.chat(
                model=self.model,
                messages=chat_history
            )
            
            ai_response = response['message']['content']
            print("Chatbot:", ai_response)
            
            # Add AI response to chat history
            chat_history.append({'role': 'assistant', 'content': ai_response})
