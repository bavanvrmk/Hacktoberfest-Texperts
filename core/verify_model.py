import sys
import time
from llm_client import LLMClient

def verify_server_load(max_retries=5, delay=2):
    """
    Verifies that the llama-server is up and the model is loaded.
    """
    print("Verifying model load status on localhost:8080...")
    client = LLMClient()
    
    for attempt in range(1, max_retries + 1):
        try:
            is_healthy = client.health_check()
            if is_healthy:
                print(f"Success! Model server is up and responding (Attempt {attempt}).")
                # Optional: Send a dummy request to warm up the model
                print("Sending warm-up request...")
                messages = [{"role": "user", "content": "Hello, are you ready?"}]
                response = client.chat_completion(messages, max_tokens=10)
                print("Warm-up response received successfully.")
                return True
            else:
                print(f"Attempt {attempt}: Server responded with non-200 status.")
        except Exception as e:
            print(f"Attempt {attempt}: Server not reachable yet. Retrying in {delay}s...")
        
        time.sleep(delay)
        
    print("Failed to verify model load after multiple attempts.")
    return False

if __name__ == "__main__":
    success = verify_server_load()
    if not success:
        sys.exit(1)
    sys.exit(0)
