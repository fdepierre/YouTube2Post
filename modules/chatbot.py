import ollama

class Chatbot:
    def __init__(self, model):
        self.model = model

    def check_ollama_running(self):
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': 'Hello'}]
            )
            return 'message' in response and 'content' in response['message']
        except Exception:
            return False

    def interactive_chat(self, transcript_file):
        if not self.check_ollama_running():
            raise Exception('Ollama service is not running. Please start Ollama.')
        
        # Open and read the content of the transcript file
        with open(transcript_file, 'r') as file:
            transcript_content = file.read()

        chat_history = [{'role': 'system', 'content': transcript_content}]
        
        while True:
            user_input = input("User: ")
            if user_input.lower() == "exit":
                print("Chatbot: Goodbye!")
                break
            
            chat_history.append({'role': 'user', 'content': user_input})
            
            response = ollama.chat(
                model=self.model,
                messages=chat_history
            )
            
            ai_response = response['message']['content']
            print("Chatbot:", ai_response)
            
            chat_history.append({'role': 'assistant', 'content': ai_response})
