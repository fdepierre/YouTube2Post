"""
Ollama Manager Module
-------------
Interactive chat and model selection for YouTube2Post.

Low-level Ollama HTTP/SDK calls are delegated to the shared package
``ollama_shared`` (also used by extract-archives).
"""

from ollama_shared import DEFAULT_HOST, DEFAULT_MODEL, OllamaService


class OllamaManager:
    """
    Manage Ollama models and interactive chat sessions about transcripts.

    Attributes:
        model (str | None): Selected model name.
        service (OllamaService): Shared Ollama client.
    """

    def __init__(self, model=None, host=DEFAULT_HOST):
        self.service = OllamaService(model=model, host=host)
        self.model = model
        if self.model is None:
            running_models = self.list_running_models()
            if len(running_models) == 1:
                self.model = running_models[0]
                self.service.model = running_models[0]
            elif len(running_models) == 0:
                raise Exception(
                    "No Ollama model is running. Please start a model with "
                    f"'ollama run {DEFAULT_MODEL}' or use -m to select."
                )

    @property
    def client(self):
        """Backward-compatible access to the underlying ollama.Client."""
        return self.service.client

    def list_available_models(self):
        try:
            return self.service.list_available_models()
        except Exception as e:
            raise Exception(f"Failed to list models: {str(e)}") from e

    def list_running_models(self):
        try:
            return self.service.list_running_models()
        except Exception as e:
            raise Exception(f"Failed to list running models: {str(e)}") from e

    def select_model(self, use_running=False, non_interactive=False):
        running_models = self.list_running_models()

        if not running_models:
            print("\nNo models are currently running. Available models:")
            available_models = self.list_available_models()
            for model in available_models:
                print(f"- {model}")
            print(
                f"\nPlease start one of these models using 'ollama run <model_name>' "
                f"(e.g. ollama run {DEFAULT_MODEL}) and try again."
            )
            raise Exception("No running models available")

        if non_interactive:
            selected = running_models[0]
            self.model = selected
            self.service.model = selected
            return selected

        if use_running:
            print("\nRunning models:")
            for i, model in enumerate(running_models, 1):
                print(f"{i}. {model} (▲)")
            if len(running_models) == 1:
                print("\nOnly one model is running. Press Enter to use it: ")
                choice = input().strip().lower()
                if not choice:
                    self.model = running_models[0]
                    self.service.model = running_models[0]
                    return running_models[0]
            while True:
                print("\nEnter the number of the model to use: ")
                choice = input().strip().lower()
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(running_models):
                        selected = running_models[choice_num - 1]
                        self.model = selected
                        self.service.model = selected
                        return selected
                    print("Invalid selection. Please try again.")
                except ValueError:
                    if not choice:
                        self.model = running_models[0]
                        self.service.model = running_models[0]
                        return running_models[0]
                    print("Invalid input. Please enter a number.")
        else:
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
                            print(
                                f"\nModel {selected_model} is not running. Please start it "
                                f"with 'ollama run {selected_model}' and try again."
                            )
                            raise Exception(
                                f"Selected model {selected_model} is not running"
                            )
                        self.model = selected_model
                        self.service.model = selected_model
                        return selected_model
                    print("Invalid selection. Please try again.")
                except ValueError:
                    if not choice:
                        for model in available_models:
                            if model in running_models:
                                self.model = model
                                self.service.model = model
                                return model
                    print("Invalid input. Please enter a number.")

    def _show_available_models(self):
        available_models = self.list_available_models()
        running_models = self.list_running_models()

        print("\nAvailable models:")
        for model in available_models:
            indicator = " (▲)" if model in running_models else ""
            print(f"- {model}{indicator}")

        if not running_models:
            print(
                f"\nPlease start one of these models using 'ollama run <model_name>' "
                f"and try again."
            )
            raise Exception("Please start a model first")
        print("\nOnly models marked with (▲) are currently running and available for use.")
        raise Exception("Please select a running model")

    def check_ollama_running(self):
        try:
            if not self.model:
                return False
            return self.service.check_model_responsive(self.model)
        except RuntimeError as e:
            raise Exception(
                f"Model {self.model} is not available. Please check your config.json "
                f"and make sure it matches an available Ollama model."
            ) from e
        except Exception:
            return False

    def interactive_chat(self, transcript_file):
        if not self.check_ollama_running():
            raise Exception("Ollama service is not running. Please start Ollama.")

        try:
            with open(transcript_file, "r", encoding="utf-8") as file:
                transcript_content = file.read()

            initial_prompt = f"""You are an AI assistant helping analyze a video transcript. 
The transcript is provided below. Please use it to answer questions about the video.

TRANSCRIPT:
{transcript_content}

Please wait for the user's question about the video."""

            chat_history = [
                {"role": "system", "content": initial_prompt},
                {
                    "role": "assistant",
                    "content": "I have the transcript ready. Please ask me any questions about the video.",
                },
            ]

            print(
                f"\nChat session started with [{self.model}▲]. Type 'exit' to end the session.\n"
            )
            print(
                "The AI has been provided with the video transcript. "
                "You can now ask questions about it.\n"
            )

            while True:
                try:
                    user_input = input("User: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ["exit", "quit", "bye", "/bye"]:
                        print("Assistant: Goodbye!")
                        break

                    chat_history.append({"role": "user", "content": user_input})
                    response = self.service.chat(chat_history, model=self.model)

                    if hasattr(response, "message"):
                        assistant_message = response.message.content
                    else:
                        assistant_message = response["message"]["content"]
                    print(f"Assistant: {assistant_message}")

                    chat_history.append(
                        {"role": "assistant", "content": assistant_message}
                    )
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
            raise Exception(f"Failed to start chat session: {str(e)}") from e
