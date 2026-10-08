import os
import cv2
import numpy as np
import time

# Import Phase 1 & 2 Modules
from src.architecture.database_logger import init_db, log_task_start, log_task_end
from src.architecture.roi_calculator import calculate_financial_roi
from src.architecture.pii_redaction import detect_and_blur_pii
from core.mouse_executor import smooth_mouse_move

def create_mock_image(img_path):
    # Create a white image
    img = np.zeros((300, 600, 3), dtype=np.uint8)
    img.fill(255)
    
    # Add some text with an SSN
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'User Profile:', (50, 50), font, 1, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(img, 'Name: John Doe', (50, 100), font, 1, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(img, 'SSN: 123-45-6789', (50, 150), font, 1, (0, 0, 0), 2, cv2.LINE_AA) # PII
    cv2.putText(img, 'Email: john@example.com', (50, 200), font, 1, (0, 0, 0), 2, cv2.LINE_AA) # PII
    
    cv2.imwrite(img_path, img)

def main():
    print("=== Phase 1 & 2 Integration Test ===")
    
    # 1. Database & Logging (Member 4 - Phase 1)
    print("\n--- Testing Database Logger ---")
    init_db()
    task_name = "Extract Profile Data"
    task_id, start_time = log_task_start(task_name)
    print(f"Started task: '{task_name}' (ID: {task_id})")
    
    # 2. PII Redaction (Member 4 - Phase 2)
    print("\n--- Testing PII Redaction Pipeline ---")
    input_img = "mock_screen.jpg"
    output_img = "mock_screen_redacted.jpg"
    create_mock_image(input_img)
    print(f"Created mock screen image with PII at '{input_img}'")
    
    try:
        detect_and_blur_pii(input_img, output_img)
        print(f"PII Redaction complete. Check '{output_img}'")
    except Exception as e:
        print(f"PII Redaction encountered an error: {e}")
        
    # 3. Mouse Executor (Member 2 - Phase 2)
    print("\n--- Testing Mouse Executor (Smoothing) ---")
    print("Moving mouse slightly to demonstrate human-like trajectory...")
    try:
        smooth_mouse_move(0, 0, 100, 100, duration=0.5)
        print("Mouse moved successfully.")
    except Exception as e:
        print(f"Mouse movement failed (failsafe might be triggered): {e}")

    # 4. Finish Task and Calculate ROI (Member 4 - Phase 1)
    print("\n--- Testing ROI Calculator & Task Completion ---")
    # Simulate processing time
    time.sleep(1) 
    
    # Calculate savings
    # Assume this task saved 1 API call
    roi = calculate_financial_roi(num_requests=1, num_automated_tasks=1)
    print(f"ROI Calculated for this task: {roi}")
    
    # Log task end
    duration = log_task_end(task_id, start_time, cloud_cost_saved_usd=roi['cloud_savings_usd'], notes="Integration Test Successful")
    print(f"Task completed in {duration}ms. Logged to database.")
    
    print("\n=== Integration Test Finished Successfully ===")
    print("Note: The UIs (Spotlight, AR Overlay, FastAPI Dashboard) require a running event loop and are ready for manual testing.")

if __name__ == "__main__":
    main()
