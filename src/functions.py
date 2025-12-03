import os
import requests
import json
from dotenv import load_dotenv
from tqdm import tqdm
import time
import tiktoken

load_dotenv()

def categorize_lookup_table(lookup_df, batch_size=None, delay=0.2, rows_per_call=10, checkpoint_path='lookup_checkpoint.parquet'):
    """
    Run Azure OpenAI on lookup table with batching, cost tracking, and checkpointing.
    
    Args:
        lookup_df: DataFrame with Spend_Data_Vendor_Number, Spend_Data_Line_Item_Text columns
        batch_size: Total rows to process (None = all unprocessed rows)
        delay: Seconds between API calls to avoid rate limiting
        rows_per_call: Number of rows to send in each API call (batching for efficiency)
        checkpoint_path: Path to save progress checkpoints
    
    Returns:
        DataFrame with populated category and sub_category columns
    """
    
    # Load config
    TENANT_ID = os.getenv("TENANT_ID")
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("SECRET_VALUE")
    SERVICE_NAME = os.getenv("SERVICE_NAME")
    DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
    API_VERSION = os.getenv("API_VERSION")
    
    # Token counting for cost tracking
    try:
        encoding = tiktoken.encoding_for_model("gpt-4o")
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    total_input_tokens = 0
    total_output_tokens = 0
    
    def get_token():
        """Get fresh access token from Azure AD."""
        token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        token_payload = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "https://cognitiveservices.azure.com/.default",
            "grant_type": "client_credentials"
        }
        response = requests.post(token_url, data=token_payload)
        response.raise_for_status()
        return response.json().get("access_token")
    
    print("Getting access token...")
    token = get_token()
    print("✓ Token received\n")
    
    api_url = f"https://{SERVICE_NAME}.openai.azure.com/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"
    
    # System prompt for categorization (batched version)
    system_prompt = """You are a Software Spend Category Expert.

Given vendor names and line item texts, classify each into:
1. category: The parent category (must match one of the categories below exactly)
2. sub_category: A more specific sub-category (must match one of the subcategories below exactly)

Use ONLY the categories and subcategories listed here:

Artificial Intelligence
- AI Code Assistant
- AI Governance, Risk & Compliance (GRC)
- AI Image Generators
- AI Sales Assistant
- Generative AI (General)
- Machine Learning Platforms
- AI Model Providers
- MCP Server

Analytics & Data
- Analytics Platform
- Business Intelligence
- Data Analytics (General)
- Data Management
- Data Platform
- Data Governance
- Data Science Platforms
- ETL Tools
- Master Data Management (MDM)
- Web Analytics

Business Management & Operations
- Business Management (General)
- Operations Management

Collaboration & Productivity
- Collaboration (General)
- Project Management (General)
- Resource Management
- Diagramming Software
- Whiteboarding
- Mind Mapping
- Wiki Software
- Knowledge Management
- Workflow Automation
- Team Collaboration
- Online Meetings
- Productivity (General)

Communication
- Email Clients
- Web Email Services
- Instant Messaging
- Personal Instant Messaging

Content & Marketing
- Content Management (General)
- Digital Asset Management (DAM)
- Engagement Platform
- Marketing Automation
- Marketing Technology
- Advertising Platforms
- Social Media Management
- Sales Enablement
- Revenue AI
- Sales & Analytics
- News & Entertainment
- Social Networks

CRM & Customer Service
- CRM (General)
- Contact Management
- Sales (General)
- Sales Tracking
- Customer Support (General)
- Customer Data Platform (CDP)
- Business Process Outsourcing (BPO)

Design & Media
- Design (General)
- Product Design
- Image Editing
- Vector Graphics
- Typography Tools
- CAD
- Animation
- Rendering
- Non-linear Editing
- Motion Graphics
- Special Effects

Development
- IDEs
- Developer Tools (General)
- Code Hosting
- Application Development
- API Tools
- Debugging Tools
- Release Management
- Testing Tools
- Testing & Automation (General)
- Website Monitoring
- Forums
- CI/CD

E-Learning & HR
- Learning Management Systems (LMS)
- E-Learning (General)
- Human Capital Management (HCM)
- Applicant Tracking Systems (ATS)
- Performance Management
- Time & Attendance
- Education Platforms

ERP & Finance
- ERP (General)
- Supply Chain & Logistics
- Procurement
- Contracting
- e-Signature
- Inventory Management
- POS Systems
- eCommerce Platforms
- Expense Management (General)
- Payroll Software
- Finance Systems
- Treasury & Risk Management
- Property Management
- Transportation & Travel
- Vendor Management Systems

Infrastructure & IT
- Infrastructure (General)
- Cloud Computing Platform
- Hosting Services
- Cloud Storage
- Content Sharing
- Data Center / Hosting
- IT Services
- IT Asset Management (ITAM)
- Asset Management (General)
- IT Management Suites
- Logging
- Observability (General)
- IT Service Management (ITSM)
- Engineers
- Application Support
- Change Mgmt / SI / Product Dev
- Subcontractors
- Tech Centers
- Resellers
- Internet of Things (IoT)
- as a Service (aaS)

Networking & Telecom
- Mobile
- Data
- Fixed Line
- VPN Clients
- Network Monitoring
- Remote Access

Security & Compliance
- Security (General)
- Cyber Security (General)
- Antivirus
- Firewalls
- VPN Software
- Identity Platform
- Password Managers
- Encryption
- MFA
- Web Application Firewall (WAF)
- Endpoint Forensics
- Network Forensics
- Compliance Software

Hardware
- Laptops / Macs
- Server Hardware
- Tech Centres

Operating Systems & Native Apps
- Windows Native Applications
- MacOS Native Applications
- OS Utilities
- OS Productivity Tools

Virtualization & Cloud
- Virtualization (General)
- Virtual Machines
- Hypervisors
- Containerization

Payment Solutions
- eCommerce Payments

Middleware
- Integration Middleware

Health
- Health Tech (General)
- Healthcare (EHR/EMR)

Respond ONLY with a valid JSON array. Each object must have "index", "category", and "sub_category".
Example format:
[{"index": 0, "category": "Development", "sub_category": "IDEs"}, {"index": 1, "category": "Security & Compliance", "sub_category": "Password Managers"}]

The index corresponds to the order of items in the input (0-based).
Do not include any other text or explanation."""

    # Filter to unprocessed rows only (for resume capability)
    unprocessed_mask = lookup_df['category'].isna()
    rows_to_process_df = lookup_df[unprocessed_mask]
    
    if batch_size:
        rows_to_process_df = rows_to_process_df.head(batch_size)
    
    if len(rows_to_process_df) == 0:
        print("✓ All rows already processed!")
        return lookup_df
    
    print(f"Processing {len(rows_to_process_df)} rows in batches of {rows_per_call}...")
    print(f"Estimated API calls: {(len(rows_to_process_df) + rows_per_call - 1) // rows_per_call}")
    
    indices = rows_to_process_df.index.tolist()
    processed_count = 0
    error_count = 0
    
    for i in tqdm(range(0, len(indices), rows_per_call), desc="Batches"):
        batch_indices = indices[i:i + rows_per_call]
        batch_rows = lookup_df.loc[batch_indices]
        
        # Build batch message
        items = []
        for j, (idx, row) in enumerate(batch_rows.iterrows()):
            vendor = row.get('Spend_Data_Vendor_Name', row.get('Spend_Data_Vendor_Number', 'Unknown'))
            line_item = row['Spend_Data_Line_Item_Text']
            items.append(f"{j}. Vendor: {vendor} | Line Item: {line_item}")
        
        user_message = "\n".join(items)
        
        # Count input tokens
        input_text = system_prompt + user_message
        input_tokens = len(encoding.encode(input_text))
        total_input_tokens += input_tokens
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        chat_payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 100 * len(batch_indices),  # Scale with batch size
            "temperature": 0.1  # Low temperature for consistent categorization
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=chat_payload)
            
            # Refresh token if expired (401 Unauthorized)
            if response.status_code == 401:
                print("\n🔄 Refreshing token...")
                token = get_token()
                headers["Authorization"] = f"Bearer {token}"
                response = requests.post(api_url, headers=headers, json=chat_payload)
            
            response.raise_for_status()
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Count output tokens
            output_tokens = len(encoding.encode(ai_response))
            total_output_tokens += output_tokens
            
            # Parse batch response
            parsed = json.loads(ai_response)
            
            for item in parsed:
                if item['index'] < len(batch_indices):
                    actual_idx = batch_indices[item['index']]
                    lookup_df.loc[actual_idx, 'category'] = item['category']
                    lookup_df.loc[actual_idx, 'sub_category'] = item['sub_category']
                    processed_count += 1
                    
        except json.JSONDecodeError:
            error_count += len(batch_indices)
            print(f"\n⚠ Batch {i//rows_per_call}: Parse error - marking rows for retry")
            for idx in batch_indices:
                lookup_df.loc[idx, 'category'] = 'PARSE_ERROR'
                lookup_df.loc[idx, 'sub_category'] = 'Retry needed'
        except requests.exceptions.RequestException as e:
            error_count += len(batch_indices)
            print(f"\n✗ Batch {i//rows_per_call}: API error: {e}")
            for idx in batch_indices:
                lookup_df.loc[idx, 'category'] = 'API_ERROR'
                lookup_df.loc[idx, 'sub_category'] = str(e)[:100]
        
        # Save checkpoint every 10 batches (100 rows with default settings)
        if (i // rows_per_call + 1) % 10 == 0:
            lookup_df.to_parquet(checkpoint_path)
            tqdm.write(f"💾 Checkpoint saved ({processed_count} rows processed)")
        
        time.sleep(delay)
    
    # Final checkpoint save
    lookup_df.to_parquet(checkpoint_path)
    
    # Cost calculation (GPT-4o-mini pricing: $0.15/1M input, $0.60/1M output)
    input_cost = (total_input_tokens / 1_000_000) * 0.15
    output_cost = (total_output_tokens / 1_000_000) * 0.60
    total_cost = input_cost + output_cost
    
    print(f"\n{'='*60}")
    print(f"✓ PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"📊 Results:")
    print(f"   Rows processed:  {processed_count:,}")
    print(f"   Errors:          {error_count:,}")
    print(f"\n📈 Token Usage:")
    print(f"   Input tokens:    {total_input_tokens:,}")
    print(f"   Output tokens:   {total_output_tokens:,}")
    print(f"   Total tokens:    {total_input_tokens + total_output_tokens:,}")
    print(f"\n💰 Cost (GPT-4o-mini pricing):")
    print(f"   Input cost:      ${input_cost:.4f}")
    print(f"   Output cost:     ${output_cost:.4f}")
    print(f"   Total cost:      ${total_cost:.4f}")
    print(f"\n💾 Checkpoint saved to: {checkpoint_path}")
    print(f"{'='*60}")
    
    return lookup_df


def retry_errors(lookup_df, delay=0.5):
    """
    Retry rows that had PARSE_ERROR or API_ERROR.
    Processes one row at a time for reliability.
    """
    error_mask = lookup_df['category'].isin(['PARSE_ERROR', 'API_ERROR'])
    error_count = error_mask.sum()
    
    if error_count == 0:
        print("✓ No errors to retry!")
        return lookup_df
    
    print(f"Retrying {error_count} rows with errors...")
    
    # Reset error rows to None so they get reprocessed
    lookup_df.loc[error_mask, 'category'] = None
    lookup_df.loc[error_mask, 'sub_category'] = None
    
    # Process with single row per call for reliability
    return categorize_lookup_table(lookup_df, batch_size=error_count, delay=delay, rows_per_call=1)
