import base64
import requests
from openai import OpenAI
import os
from dotenv import load_dotenv
import os

# Load environment variables from .env
#load_dotenv()
# Access your API key
api_key = os.getenv("OPENAI_KEY")

# Function to encode the image
def _encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')        

def gpt(text,
        model_name,
        image_path=list(),  
        system_prompt='You are a helpful assistant.', 
        temperature=1):
    
    # Prepare content for system and user-side
    system_content = [
            {
                "type": "text",
                "text": system_prompt
            }
          ]
    
    user_content = [
            {
                "type": "text",
                "text": text
            }
          ]
    
    # Add image to user content if the user input image paths
    if len(image_path) != 0:
        for i in range(len(image_path)):
            # Encode image
            base64_image = _encode_image(image_path[i])

            image_dict = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "low"
                }
            }
            user_content.append(image_dict)

    # Request to server
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model_name,
        "messages": [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": user_content
        }
        ],
        "max_tokens": 500,
        "temperature": temperature
    }

    # Get response
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response_json = response.json()
    output = response_json['choices'][0]['message']['content']
    return output
