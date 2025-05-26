"""
Ollama Manager Module
-------------
This module implements a comprehensive manager for interacting with Ollama AI models.
It provides functionality for:
- Model management (listing, selecting, and verifying models)
- Interactive chat sessions with AI models about video transcripts
- Runtime model selection from available or running instances
- Error handling and graceful session management

The module is designed to be both user-friendly for interactive use and
robust for programmatic integration.
"""

from ollama import Client

class OllamaManager:
    """
    A class to manage Ollama AI models and facilitate interactive chat sessions.
    
    This class provides comprehensive functionality for working with Ollama models,
    including:
    - Model discovery and selection (both available and running models)
    - Interactive chat sessions with proper error handling
    - Service availability verification
    - Runtime model switching capabilities
    
    The class is designed to handle various edge cases and provide a smooth
    user experience, whether used interactively or programmatically.
    
    Attributes:
        model (str, optional): Name of the Ollama model to use. If None, auto-select.
            Can be set during initialization or selected at runtime.
        client (ollama.Client): Client instance for communicating with the Ollama service.
    """

    def __init__(self, model=None, host='http://localhost:11434'):
        """
        Initialize the OllamaManager with an optional model specification.
        By default, uses the only running model if just one is active.
        Args:
            model (str, optional): Name of the Ollama model to use. If None, auto-select.
            host (str): Ollama API host URL (default: 'http://localhost:11434').
        """
        self.model = model
        self.client = Client(host=host)
        if self.model is None:
            running_models = self.list_running_models()
            if len(running_models) == 1:
                self.model = running_models[0]
            elif len(running_models) == 0:
                raise Exception("No Ollama model is running. Please start a model with 'ollama run <model>' or use -m to select.")
            # If multiple models are running, require explicit selection with -m.

        
    def list_available_models(self):
        """
        List all available models in the Ollama installation.
        
        This method queries the Ollama service for all installed models,
        regardless of whether they are currently running. The returned
        model names can be used with 'ollama run' to start a model.
        
        Returns:
            list[str]: A list of model names with tags (e.g., ['llama3.2:latest', 'gemma3:4b', ...])
        Raises:
            Exception: If unable to connect to Ollama service or if the
                service returns an unexpected response format
        """
        try:
            result = self.client.list()
            if hasattr(result, 'models'):
                # Return the full model name with tag
                return [str(model).split("'")[1] for model in result.models]
            return []
        except Exception as e:
            raise Exception(f'Failed to list models: {str(e)}')
    
    def list_running_models(self):
        """
        List all currently running model instances in Ollama.
        
        This method queries the Ollama service for models that are currently
        running and available for immediate use. Running models can be used
        directly without needing to start them first.
        
        Returns:
            list[str]: A list of model names that are currently running,
                with version tags (e.g., ['llama3.2:latest', 'gemma3:4b'])
        Raises:
            Exception: If unable to connect to Ollama service or if the
                service returns an unexpected response format
        """
        try:
            result = self.client.ps()
            if hasattr(result, 'models'):
                # Return the full model name with tag
                return [str(model).split("'")[1] for model in result.models]
            return []
        except Exception as e:
            raise Exception(f'Failed to list running models: {str(e)}')
            
    def select_model(self, use_running=False, non_interactive=False):
        """
        Select a model to use, either from running models or available models.
        
        This method provides an interface for selecting an Ollama model.
        If use_running is True, it first attempts to select from currently running
        models. If no running models are found, it shows available models that can be started.
        
        The selection process handles various scenarios:
        - Single running model: User can press Enter to use it (auto-selected in non-interactive mode)
        - Multiple running models: User can select by number (first model auto-selected in non-interactive mode)
        - No running models: Shows available models that can be started and raises an exception
        
        Args:
            use_running (bool): If True, try to select from running models first.
                If False or if no running models are selected, show available models.
            non_interactive (bool): If True, automatically select the first running model
                without user input. Raises an exception if no models are running.
            
        Returns:
            str: Name of the selected model without version tag
            
        Raises:
            Exception: If no models are available, if user cancels selection,
                or if there are connection issues with the Ollama service
        """
        running_models = self.list_running_models()
        
        # If no running models, show error regardless of mode
        if not running_models:
            print("\nNo models are currently running. Available models:")
            available_models = self.list_available_models()
            for model in available_models:
                print(f"- {model}")
            print("\nPlease start one of these models using 'ollama run <model_name>' and try again.")
            raise Exception("No running models available")
        
        # Non-interactive mode: auto-select first running model
        if non_interactive:
            return running_models[0]
        
        # Interactive mode with running models
        if use_running:
            print("\nRunning models:")
            for i, model in enumerate(running_models, 1):
                print(f"{i}. {model} (▲)")
            if len(running_models) == 1:
                print("\nOnly one model is running. Press Enter to use it: ")
                choice = input().strip().lower()
                if not choice:  # User pressed Enter
                    return running_models[0]
            while True:
                print("\nEnter the number of the model to use: ")
                choice = input().strip().lower()
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(running_models):
                        return running_models[choice_num - 1]
                    print("Invalid selection. Please try again.")
                except ValueError:
                    if not choice:  # User pressed Enter with multiple models
                        return running_models[0]
                    print("Invalid input. Please enter a number.")
        else:
            # Show all available models (not just running ones)
            available_models = self.list_available_models()
            print("\nAvailable models:")
            for i, model in enumerate(available_models, 1):
                indicator = " (▲)" if model in running_models else ""
                print(f"{i}. {model}{indicator}")
            while True:
                print("\nEnter the number of the model to use: ")
                choice = input().strip()
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(available_models):
                        selected_model = available_models[choice_num - 1]
                        if selected_model not in running_models:
                            print(f"\nModel {selected_model} is not running. Please start it with 'ollama run {selected_model}' and try again.")
                            raise Exception(f"Selected model {selected_model} is not running")
                        return selected_model
                    print("Invalid selection. Please try again.")
                except ValueError:
                    if not choice:  # User pressed Enter
                        # Find first running model in the list
                        for model in available_models:
                            if model in running_models:
                                return model
                    print("Invalid input. Please enter a number.")
            
    def _show_available_models(self):
        """
        Show available models and prompt user to start one.
        
        This internal helper method displays a list of all available models
        and provides instructions for starting them using the 'ollama run'
        command. It's typically called when no running models are available.
        
        Raises:
            Exception: Always raises an exception with instructions for starting
                a model using 'ollama run'. This is part of the expected flow
                when a model needs to be started.
        """
        available_models = self.list_available_models()
        running_models = self.list_running_models()
        
        print("\nAvailable models:")
        for model in available_models:
            indicator = " (▲)" if model in running_models else ""
            print(f"- {model}{indicator}")
            
        if not running_models:
            print("\nPlease start one of these models using 'ollama run <model_name>' and try again.")
            raise Exception("Please start a model first")
        else:
            print("\nOnly models marked with (▲) are currently running and available for use.")
            raise Exception("Please select a running model")

    def check_ollama_running(self):
        """
        Check if the Ollama service is running and the model is available.
        
        This method performs a comprehensive check by:
        1. Attempting to connect to the Ollama service
        2. Verifying that the specified model exists and is accessible
        3. Ensuring the model can process basic requests
        
        The check is performed by sending a simple test message ('Hello')
        and verifying the response format.
        
        Returns:
            bool: True if both the Ollama service is running and the specified
                model is available and responsive. False if the service is down
                or unresponsive.
            
        Raises:
            Exception: If the specified model is not available in Ollama,
                with a helpful message suggesting to check the config.json
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
        
        This method provides a robust interactive chat interface where users can
        discuss the content of a video transcript with the AI model. The session
        includes:
        - Proper handling of empty inputs and interrupts
        - Clear session start/end messages
        - Multiple exit commands ('exit', 'quit', 'bye', '/bye')
        - Graceful error handling with helpful messages
        
        The chat maintains a conversation history to provide context for the
        AI model's responses. The transcript content is provided as initial
        system context.
        
        Args:
            transcript_file (str): Path to the transcript file to discuss.
                The file should be readable and contain the transcript text.
            
        Raises:
            Exception: If the Ollama service is not running, if the model
                is not available, or if there are issues reading the transcript file.
                All exceptions include helpful error messages for resolution.
        """
        if not self.check_ollama_running():
            raise Exception('Ollama service is not running. Please start Ollama.')
        
        try:
            # Open and read the content of the transcript file
            with open(transcript_file, 'r') as file:
                transcript_content = file.read()

            # Initialize chat with system message containing transcript
            initial_prompt = f"""You are an AI assistant helping analyze a video transcript. 
The transcript is provided below. Please use it to answer questions about the video.

TRANSCRIPT:
{transcript_content}

Please wait for the user's question about the video."""

            chat_history = [
                {'role': 'system', 'content': initial_prompt},
                {'role': 'assistant', 'content': 'I have the transcript ready. Please ask me any questions about the video.'}
            ]

            # Display model badge with running indicator
            print(f"\nChat session started with [{self.model}▲]. Type 'exit' to end the session.\n")
            print("The AI has been provided with the video transcript. You can now ask questions about it.\n")

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
