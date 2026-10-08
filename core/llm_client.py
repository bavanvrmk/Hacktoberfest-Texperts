import json
import urllib.request
import urllib.error

class LLMClient:
    def __init__(self, base_url="http://localhost:8080/v1"):
        self.base_url = base_url

    def chat_completion(self, messages, temperature=0.0, max_tokens=256):
        """
        Calls the /v1/chat/completions endpoint.
        messages: list of dict with 'role' and 'content'
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers, 
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
        except urllib.error.URLError as e:
            raise Exception(f"Failed to communicate with LLM server: {e}")

    def health_check(self):
        """
        Checks if the /v1/models endpoint is reachable.
        """
        url = f"{self.base_url}/models"
        req = urllib.request.Request(url, method='GET')
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    return True
                return False
        except urllib.error.URLError:
            return False

if __name__ == "__main__":
    client = LLMClient()
    print("Base URL:", client.base_url)
