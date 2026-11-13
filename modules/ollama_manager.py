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

import time

from ollama import Client

try:
    from .progress import Spinner
    from . import ui
except ImportError:  # imported as a top-level module
    from progress import Spinner
    import ui

# Ollama only reads the first few thousand tokens of a prompt by default
# (num_ctx), so a long transcript would be cut off. The context is sized from
# the conversation instead: as small as possible, because a context that does
# not fit in GPU memory makes answers several times slower.
CHARS_PER_TOKEN = 3.5      # measured ~4.2 on French/English transcripts; kept low as a margin
ANSWER_TOKENS = 2048       # room for the model's answer
CONTEXT_STEP = 8192        # round up, so the model is rarely reloaded with a new size
MIN_CONTEXT = 8192


def context_size(messages, max_context=None):
    """Return a num_ctx large enough for the messages plus an answer."""
    chars = sum(len(m['content']) for m in messages)
    needed = int(chars / CHARS_PER_TOKEN) + ANSWER_TOKENS
    size = max(MIN_CONTEXT, -(-needed // CONTEXT_STEP) * CONTEXT_STEP)
    if max_context:
        size = min(size, max_context)
    return size


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
                return [model.model for model in result.models]
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
                return [model.model for model in result.models]
            return []
        except Exception as e:
            raise Exception(f'Failed to list running models: {str(e)}')
            
    def choose_model(self, ask=False):
        """
        Choose the Ollama model for the chat. Ollama loads it on the first
        question, so it does not need to be started with 'ollama run'.

        Without ask, the choice is automatic when it is unambiguous: the only
        running model, or the only installed one. Otherwise (or with ask) the
        installed models are listed and the user picks one; Enter takes the
        default (the running model, else the most recently installed one).

        Returns:
            str: The model name with its tag (e.g. 'qwen3.5:4b')

        Raises:
            Exception: If no model is installed or the user cancels.
        """
        installed = self.list_available_models()  # most recently installed first
        if not installed:
            raise Exception("No Ollama model is installed. Install one, for example: "
                            "ollama pull qwen3.5:4b")
        running = [m for m in self.list_running_models() if m in installed]
        default = running[0] if running else installed[0]

        if not ask:
            if len(running) == 1:
                return running[0]
            if len(installed) == 1:
                return installed[0]

        print("Installed Ollama models (▲ = already loaded):")
        for i, model in enumerate(installed, 1):
            print(f"  {ui.style(str(i), 'bold', 'cyan')}. {model}{' ▲' if model in running else ''}")
        while True:
            try:
                choice = input(f"Model number [Enter = {default}]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                raise Exception("No model selected")
            if not choice:
                return default
            if choice.isdigit() and 1 <= int(choice) <= len(installed):
                return installed[int(choice) - 1]
            print(f"Please enter a number between 1 and {len(installed)}.")

    def select_model(self, use_running=False, non_interactive=False):
        """
        Select a model (kept for compatibility, see choose_model).

        Args:
            use_running (bool): Unused; running models are always preferred.
            non_interactive (bool): Return the default model without asking.
        """
        if non_interactive:
            installed = self.list_available_models()
            if not installed:
                raise Exception("No Ollama model is installed")
            running = [m for m in self.list_running_models() if m in installed]
            return running[0] if running else installed[0]
        return self.choose_model(ask=True)

    def model_details(self):
        """Return (maximum context length or None, model supports thinking)."""
        try:
            details = self.client.show(self.model)
        except Exception:
            return None, False
        max_context = None
        for key, value in (details.modelinfo or {}).items():
            if key.endswith('.context_length'):
                max_context = int(value)
        return max_context, 'thinking' in (details.capabilities or [])

    def check_ollama_running(self):
        """
        Check if the Ollama service is running and the model is available.
        
        The check asks Ollama for the model's details, which needs no text
        generation: sending a test message would make thinking models reason
        for ~10 s, and load the model with a context size the chat then changes.

        Returns:
            bool: True if the Ollama service is running and the specified
                model is installed. False if the service is down or unresponsive.

        Raises:
            Exception: If the specified model is not available in Ollama.
        """
        try:
            if self.model:
                self.client.show(self.model)
            else:  # no model chosen yet: just check the service
                self.client.list()
            return True
        except Exception as e:
            message = str(e).lower()
            if "not found" in message or "no such model" in message:
                raise Exception(f"Model {self.model} is not available. "
                                "Check the installed models with 'ollama list'.")
            return False

    def _stream_answer(self, chat_history, max_context, chat_options, first):
        """
        Ask the model and print its answer as it is written. Until the first
        words arrive, a spinner shows that the model is working: the first
        question takes longest, as the model reads the whole transcript.

        Returns:
            str: The answer, or None if the user interrupted it with Ctrl+C.
        """
        # A context that holds the whole conversation
        num_ctx = context_size(chat_history, max_context)
        label = ("Reading the transcript and preparing the answer..." if first
                 else "Preparing the answer...")
        parts = []
        last = None
        start = time.monotonic()
        indicator = Spinner(label)
        try:
            with indicator:
                stream = self.client.chat(
                    model=self.model,
                    messages=chat_history,
                    options={'num_ctx': num_ctx},
                    stream=True,
                    **chat_options,
                )
                for chunk in stream:
                    last = chunk
                    text = chunk['message']['content']
                    if not text:
                        continue
                    if not parts:
                        indicator.stop()
                        print(ui.style("Assistant: ", 'bold', 'magenta'), end='', flush=True)
                    parts.append(text)
                    print(text, end='', flush=True)
        except KeyboardInterrupt:
            ui.warn("\n[Answer interrupted]\n")
            return None
        print("\n" + ui.style(f"({time.monotonic() - start:.0f}s)", 'dim'))
        self._answer_details(last, num_ctx)
        print()
        return ''.join(parts)

    def _answer_details(self, last, num_ctx):
        """In verbose mode, show the token counts and speed of an answer."""
        if not ui.verbose or not last:
            return
        get = lambda key: last.get(key) if isinstance(last, dict) else getattr(last, key, None)
        prompt, generated = get('prompt_eval_count'), get('eval_count')
        eval_ns, load_ns = get('eval_duration'), get('load_duration')
        if generated and eval_ns:
            ui.detail(f"Read {prompt or 0} new tokens, wrote {generated} tokens at "
                      f"{generated / (eval_ns / 1e9):.1f} tokens/s"
                      + (f"; model load {load_ns / 1e9:.1f}s" if load_ns and load_ns > 5e8 else ""))
        try:
            for m in self.client.ps().models:
                if m.model == self.model and m.size:
                    ui.detail(f"{m.size_vram / m.size:.0%} of the model on the GPU "
                              f"({m.size / 1e9:.1f} GB with a {num_ctx}-token context)")
        except Exception:
            pass

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
            with open(transcript_file, 'r', encoding='utf-8') as file:
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

            max_context, can_think = self.model_details()
            # Thinking models (qwen3.5, gemma4...) first write a long hidden
            # reasoning: measured 5x slower for no visible gain on summaries.
            chat_options = {'think': False} if can_think else {}
            num_ctx = context_size(chat_history, max_context)
            transcript_tokens = int(len(transcript_content) / CHARS_PER_TOKEN)
            if max_context and transcript_tokens + ANSWER_TOKENS > max_context:
                ui.warn(f"\nWarning: the transcript (~{transcript_tokens} tokens) is longer than the "
                      f"context of {self.model} ({max_context} tokens); its beginning will be cut off.")

            # Display model badge with running indicator
            print(f"Chat session started with [{ui.style(self.model, 'bold')}▲]. Type 'exit' to end the session.\n")
            print(f"Context: {num_ctx} tokens (transcript ~{transcript_tokens} tokens).")
            ui.detail(f"Model maximum context: {max_context or 'unknown'} tokens; "
                      f"thinking {'off' if can_think else 'not supported'}; "
                      f"~{CHARS_PER_TOKEN} characters per token assumed")
            print("The AI has been provided with the video transcript. You can now ask questions about it.\n")

            # Start interactive chat loop
            print("While an answer is being written, Ctrl+C stops it.\n")
            questions = 0
            while True:
                try:
                    user_input = input(ui.style("User: ", 'bold', 'green')).strip()
                    
                    # Skip empty input
                    if not user_input:
                        continue
                        
                    # Check for various exit commands
                    if user_input.lower() in ["exit", "quit", "bye", "/bye"]:
                        print(ui.style("Assistant: ", 'bold', 'magenta') + "Goodbye!")
                        break
                    
                    # Add user message to chat history
                    chat_history.append({'role': 'user', 'content': user_input})
                    
                    assistant_message = self._stream_answer(
                        chat_history, max_context, chat_options, first=(questions == 0))
                    questions += 1
                    if assistant_message is None:  # interrupted with Ctrl+C
                        chat_history.pop()
                        continue

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
                    ui.error(f"\nError during chat: {str(e)}")
                    print("Please try again or type 'exit' to end the session.")
        except Exception as e:
            raise Exception(f'Failed to start chat session: {str(e)}')
