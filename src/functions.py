import os
import asyncio
import aiohttp
import pandas as pd
import json
import time
from dotenv import load_dotenv
from itables import show

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
TENANT_ID = os.getenv("TENANT_ID", "autodesk.onmicrosoft.com")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("SECRET_VALUE")
SERVICE_NAME = os.getenv("SERVICE_NAME")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
API_VERSION = os.getenv("API_VERSION", "2024-02-01")

# Limit concurrent requests to avoid rate limiting
MAX_CONCURRENT_REQUESTS = 5 

def get_access_token():
    """
    Retrieves the Azure AD OAuth2 access token synchronously.
    (Tokens last for ~1 hour, so we don't need to fetch this async every time)
    """
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://cognitiveservices.azure.com/.default",
        "grant_type": "client_credentials"
    }
    
    try:
        # We use 'requests' here just for the initial token fetch
        import requests
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

async def categorize_batch(session, batch_df, token, batch_id):
    """
    Sends a batch of rows to Azure OpenAI for categorization.
    """
    api_url = f"https://{SERVICE_NAME}.openai.azure.com/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"
    
    # Convert rows to a string format for the prompt
    # Adjust columns based on what you actually have in your data
    # For example: 'Vendor Name', 'Description', 'Amount'
    records_text = batch_df.to_json(orient="records") 

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "You are a data categorization assistant. "
        "Analyze the following JSON list of transactions. "
        "For each transaction, assign a 'Category' (e.g., Software, Hardware, Services, Travel). "
        "Return ONLY a valid JSON list of objects with the original 'id' and the new 'Category'. "
        "Do not include markdown formatting."
    )

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": records_text}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    }

    try:
        async with session.post(api_url, headers=headers, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                print(f"Batch {batch_id} failed: {response.status} - {text}")
                return []
            
            result = await response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse the JSON response from AI
            # Using a robust parsing strategy is recommended here (e.g. cleaning markdown code blocks)
            if content.startswith(""):
                content = content.replace("", "").replace("```", "")
            
            return json.loads(content.strip())
            
    except Exception as e:
        print(f"Error processing batch {batch_id}: {e}")
        return []

async def process_dataframe(df, batch_size=20):
    """
    Main async loop to process the entire dataframe in batches.
    """
    token = get_access_token()
    if not token:
        print("Failed to authenticate.")
        return None

    # Create a temporary ID column to map results back reliably
    df = df.copy()
    df['id'] = range(len(df))
    
    # We only send relevant columns to save tokens
    # CHANGE THESE to your actual column names
    cols_to_send = ['id', 'Vendor', 'Description'] 
    # Ensure these columns exist, otherwise fall back to all
    work_df = df[cols_to_send] if set(cols_to_send).issubset(df.columns) else df

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        
        # create batches
        for i in range(0, len(work_df), batch_size):
            batch = work_df.iloc[i : i + batch_size]
            tasks.append(categorize_batch(session, batch, token, i // batch_size))
        
        print(f"Starting processing of {len(tasks)} batches...")
        start_time = time.time()
        
        # Run all batches
        results = await asyncio.gather(*tasks)
        
        print(f"Processing complete in {time.time() - start_time:.2f} seconds.")

    # Flatten results (list of lists -> list of dicts)
    flat_results = [item for sublist in results for item in sublist]
    
    # Merge results back to original dataframe
    results_df = pd.DataFrame(flat_results)
    
    if not results_df.empty and 'id' in results_df.columns:
        final_df = df.merge(results_df[['id', 'Category']], on='id', how='left')
        return final_df
    else:
        print("No valid results returned or merging failed.")
        return df

# Example Usage Block
if __name__ == "__main__":
    # Create dummy data for testing
    data = {
        "Vendor": ["Microsoft", "Delta Air Lines", "Uber", "AWS", "Staples"],
        "Description": ["Azure Subscription", "Flight to NY", "Ride to airport", "Hosting fees", "Office supplies"],
        "Amount": [1000, 500, 45, 200, 150]
    }
    df = pd.DataFrame(data)
    
    # Run the async process
    result_df = asyncio.run(process_dataframe(df, batch_size=2))
    print("\n--- Final Result ---")
    print(result_df)### Key Features of this Code:

    """
1.  **`get_access_token`**: Reuses your exact auth logic (Service Principal + Client Credentials).
2.  **`aiohttp`**: Used instead of `requests` to allow multiple batches to fly at once.
3.  **`MAX_CONCURRENT_REQUESTS`**: Limits parallel calls so you don't get rate-limited (429 errors) by Azure.
4.  **Batching**: Groups rows (default 20) to save time.
5.  **ID Mapping**: Adds a temporary `id` column to ensure the AI's answers attach to the correct original row (AI can sometimes skip rows or reorder them).
"""