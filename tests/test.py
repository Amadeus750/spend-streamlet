import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
TENANT_ID = os.getenv("TENANT_ID", "autodesk.onmicrosoft.com")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("SECRET_VALUE")

# OpenAI Configuration
SERVICE_NAME = os.getenv("SERVICE_NAME")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
API_VERSION = os.getenv("API_VERSION")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Please set CLIENT_ID and SECRET_VALUE in your .env file")

url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

payload = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "https://cognitiveservices.azure.com/.default",
    "grant_type": "client_credentials"
}

token = None

try:
    response = requests.post(url, data=payload)
    response.raise_for_status() # Raise an exception for HTTP errors
    token = response.json().get("access_token")
    print(f"Token received successfully: {token[:10]}... (truncated)")
except requests.exceptions.RequestException as e:
    print(f"Error getting token: {e}")
    if 'response' in locals():
        print(f"Response body: {response.text}")

# Use token to call openai
if token:
    print(f"\nCalling Azure OpenAI (Deployment: {DEPLOYMENT_NAME})...")
    
    # Correct Azure OpenAI URL structure
    api_url = f"https://{SERVICE_NAME}.openai.azure.com/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    chat_payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are an AI assistant that helps employees with their questions."
            },
            {
                "role": "user",
                "content": "What is the smartest way to run ai on a dataframe in python that is large and has a lot of columns and rows?"
            }
        ],
        "max_tokens": 1000
        # Note: 'model' parameter is NOT used here in Azure OpenAI; the deployment name in URL determines the model.
    }

    try:
        chat_response = requests.post(api_url, headers=headers, json=chat_payload)
        
        # specific check for 404 (Deployment not found) or 401 (Unauthorized)
        if chat_response.status_code != 200:
             print(f"Request failed with status code: {chat_response.status_code}")
             print(f"Response text: {chat_response.text}")
        
        chat_response.raise_for_status()
        result = chat_response.json()
        print("\n--- AI Response ---")
        print(result['choices'][0]['message']['content'])
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenAI: {e}")
