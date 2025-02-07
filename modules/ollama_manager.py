"""
Ollama Manager Module
-------------
This module implements an interactive chat manager using the Ollama API.
It provides functionality to have conversations with an AI model about
the content of video transcripts.
"""

from ollama import Client

class OllamaManager:
    """
    A class to handle interactive chat sessions using Ollama models.
    
    This class provides methods to interact with Ollama AI models,
    enabling conversations about video transcript content. It includes
    service availability checking, model management, and interactive chat functionality.
    
    Attributes:
        model (str): Name of the Ollama model to use for chat
    """

    def __init__(self, model=None, host='http://localhost:11434'):
        """
        Initialize the OllamaManager with a specific Ollama model.
        
        Args:
            model (str, optional): Name of the Ollama model to use (e.g., 'deepseek-r1')
            host (str): Ollama API host URL (default: 'http://localhost:11434')
        """
        self.model = model
        self.client = Client(host=host)
        
    def list_available_models(self):
        """
        List all available models in the Ollama installation.
        
        Returns:
            list: A list of model names
                
        Raises:
            Exception: If unable to connect to Ollama service
        """
        try:
            result = self.client.list()
            if hasattr(result, 'models'):
                return [str(model).split("'")[1].split(':')[0] for model in result.models]
            return []
        except Exception as e:
            raise Exception(f'Failed to list models: {str(e)}')
    
    def list_running_models(self):
        """
        List all currently running model instances in Ollama.
        
        Returns:
            list: A list of model names that are currently running
                
        Raises:
            Exception: If unable to connect to Ollama service
        """
        try:
            result = self.client.ps()
            if hasattr(result, 'models'):
                return [str(model).split("'")[1].split(':')[0] for model in result.models]
            return []
        except Exception as e:
            raise Exception(f'Failed to list running models: {str(e)}')
            
    def select_model(self, use_running=False):
        """
        Select a model to use, either from running models or available models.
        
        Args:
            use_running (bool): If True, try to select from running models first
            
        Returns:
            str: Selected model name
            
        Raises:
            Exception: If no models are available or if user cancels selection
        """
        if use_running:
            running_models = self.list_running_models()
            if not running_models:
                print("\nNo models are currently running. Available models:")
                available_models = self.list_available_models()
                for model in available_models:
                    print(f"- {model}")
                print("\nPlease start one of these models using 'ollama run <model_name>' and try again.")
                raise Exception("No running models available")
                
            print("\nRunning models:")
            for i, model in enumerate(running_models, 1):
                print(f"{i}. {model}")
                
            if len(running_models) == 1:
                print("\nOnly one model is running. Press Enter to use it, or type 'no' to list available models: ")
                choice = input().strip().lower()
                if choice == 'no':
                    return self._show_available_models()
                return running_models[0]
            
            while True:
                print("\nEnter the number of the model to use, or type 'no' to list available models: ")
                choice = input().strip().lower()
                if choice == 'no':
                    return self._show_available_models()
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(running_models):
                        return running_models[choice_num - 1]
                    print("Invalid selection. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'no'.")
        else:
            return self._show_available_models()
            
    def _show_available_models(self):
        """
        Show available models and prompt user to start one.
        
        Raises:
            Exception: Always raises an exception with instructions
        """
        available_models = self.list_available_models()
        print("\nAvailable models:")
        for model in available_models:
            print(f"- {model}")
        print("\nPlease start one of these models using 'ollama run <model_name>' and try again.")
        raise Exception("Please start a model first")

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
            response = self.client.chat(
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
        
        try:
            # Open and read the content of the transcript file
            with open(transcript_file, 'r') as file:
                transcript_content = file.read()

            # Initialize chat history with transcript as system context
            chat_history = [{'role': 'system', 'content': transcript_content}]
            
            print("\nChat session started. Type 'exit' to end the session.\n")
            
            # Start interactive chat loop
            while True:
                try:
                    user_input = input("User: ").strip()
                    
                    # Skip empty input
                    if not user_input:
                        continue
                        
                    # Check for various exit commands
                    if user_input.lower() in ["exit", "quit", "bye", "/bye"]:
                        print("Assistant: Goodbye!")
                        break
                    
                    # Add user message to chat history
                    chat_history.append({'role': 'user', 'content': user_input})
                    
                    # Get AI response
                    response = self.client.chat(
                        model=self.model,
                        messages=chat_history
                    )
                    
                    # Extract and print assistant's response
                    assistant_message = response['message']['content']
                    print(f"Assistant: {assistant_message}")
                    
                    # Add assistant's response to conversation history
                    chat_history.append({
                        'role': 'assistant',
                        'content': assistant_message
                    })
                except KeyboardInterrupt:
                    print("\nChat session terminated by user.")
                    break
                except EOFError:
                    print("\nChat session terminated.")
                    break
                except Exception as e:
                    print(f"\nError during chat: {str(e)}")
                    print("Please try again or type 'exit' to end the session.")
        except Exception as e:
            raise Exception(f'Failed to start chat session: {str(e)}')
