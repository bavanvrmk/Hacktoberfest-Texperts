import json
import base64
from .llm_client import LLMClient

# System prompt forcing the model to return JSON with [x1, y1, x2, y2]
VISION_SYSTEM_PROMPT = """
You are a GUI grounding assistant. Your task is to locate the requested UI element on the screen.
You must return your answer ONLY as a JSON object with the following schema:
{
    "target_found": true/false,
    "confidence": 0.0-1.0,
    "bounding_box": [x1, y1, x2, y2]
}
x1, y1 represent the top-left corner and x2, y2 represent the bottom-right corner as normalized coordinates (0.0 to 1.0) relative to the image dimensions.
Do not include any other text or markdown formatting outside the JSON block.
"""

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

class VisionGrounder:
    def __init__(self, client=None):
        self.client = client or LLMClient()
        
    def build_prompt(self, target_description, base64_image):
        """Constructs the vision prompt payload."""
        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": f"Locate: {target_description}"
                    }
                ]
            }
        ]
        return messages

    def parse_coordinate_response(self, response_text):
        """
        Parses and enforces the JSON schema for coordinates.
        """
        # Strip markdown code blocks if the model wrapped the JSON
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        try:
            data = json.loads(clean_text)
            
            # JSON Schema Enforcement
            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")
            if "target_found" not in data or "bounding_box" not in data:
                raise ValueError("Missing required keys in JSON")
                
            if data["target_found"]:
                box = data["bounding_box"]
                if not isinstance(box, list) or len(box) != 4:
                    raise ValueError("bounding_box must be a list of 4 coordinates")
                
                # Check normalized bounds
                for coord in box:
                    if not (0.0 <= coord <= 1.0):
                        raise ValueError("Coordinates must be normalized between 0.0 and 1.0")
                        
            return data
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to decode JSON from model: {e}\nRaw output: {response_text}")

    def find_element(self, image_path, target_description):
        """End-to-end pipeline to find an element."""
        b64_img = encode_image_to_base64(image_path)
        messages = self.build_prompt(target_description, b64_img)
        
        response = self.client.chat_completion(messages, temperature=0.1, max_tokens=150)
        
        if "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0]["message"]["content"]
            return self.parse_coordinate_response(content)
        else:
            raise Exception(f"Unexpected response format: {response}")

if __name__ == "__main__":
    print("Vision Grounding Pipeline initialized.")
    # Test parsing functionality
    dummy_grounder = VisionGrounder()
    mock_response = '```json\n{"target_found": true, "confidence": 0.95, "bounding_box": [0.1, 0.2, 0.3, 0.4]}\n```'
    print("Testing parser...")
    parsed = dummy_grounder.parse_coordinate_response(mock_response)
    print(f"Parsed Successfully: {parsed}")
