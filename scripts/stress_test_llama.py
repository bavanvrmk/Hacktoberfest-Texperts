import time
import sys
import threading
import os

# Ensure core is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.llm_client import LLMClient

def simulate_vision_request(client, worker_id, iterations=10):
    """
    Simulates a continuous automation loop sending requests to the local LLM.
    """
    success = 0
    fail = 0
    start_time = time.time()
    
    for i in range(iterations):
        try:
            # Using a lightweight dummy prompt to stress the server concurrency
            messages = [{"role": "user", "content": f"Stress test {worker_id}-{i}. Reply OK."}]
            # Fast inference settings simulating Phase 3 tweaks
            response = client.chat_completion(messages, temperature=0.0, max_tokens=10)
            success += 1
        except Exception as e:
            print(f"[Worker {worker_id}] Request failed: {e}")
            fail += 1
            
    elapsed = time.time() - start_time
    print(f"[Worker {worker_id}] Finished in {elapsed:.2f}s | Success: {success} | Fail: {fail}")

def run_stress_test(concurrent_workers=4, iterations_per_worker=25):
    print(f"=== Starting Local LLM Stress Test ===")
    print(f"Workers: {concurrent_workers} | Iterations/Worker: {iterations_per_worker}")
    
    client = LLMClient()
    if not client.health_check():
        print("WARNING: llama-server is offline. Please run start_server.ps1 first.")
        
    threads = []
    for i in range(concurrent_workers):
        t = threading.Thread(target=simulate_vision_request, args=(client, i, iterations_per_worker))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    print("=== Stress Test Completed ===")

if __name__ == "__main__":
    run_stress_test()
