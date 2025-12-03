# Install tiktoken if you haven't already
# !pip install tiktoken

import tiktoken

def calculate_exact_ai_cost(df, columns_to_send, model="gpt-4o-mini"):
    """
    Calculate exact cost based on actual token count of the dataframes columns.
    """
    try:
        encoding = tiktoken.encoding_for_model("gpt-4o") # gpt-4o-mini uses same tokenizer
    except:
        encoding = tiktoken.get_encoding("cl100k_base") # fallback

    # Combine columns into a single string per row to mimic what you'd send to the API
    # e.g. "Vendor: Microsoft, Description: Cloud Service"
    def count_row_tokens(row):
        text = " ".join([f"{col}: {str(row[col])}" for col in columns_to_send])
        return len(encoding.encode(text))

    print("Counting tokens per row...")
    # Create a temporary column for token counts (not modifying original df permanently if you don't save)
    token_counts = df.apply(count_row_tokens, axis=1)
    
    total_input_tokens = token_counts.sum()
    avg_tokens_per_row = token_counts.mean()
    max_tokens_row = token_counts.max()
    
    # Pricing (per 1M tokens)
    pricing = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o":      {"input": 2.50, "output": 10.00},
    }
    
    # Estimate output tokens (assumes ~50 tokens for category + reason)
    total_output_tokens = len(df) * 50
    
    input_cost = (total_input_tokens / 1_000_000) * pricing[model]["input"]
    output_cost = (total_output_tokens / 1_000_000) * pricing[model]["output"]
    total_cost = input_cost + output_cost
    
    print(f"\n--- Exact Cost Analysis for {len(df):,} rows ({model}) ---")
    print(f"Columns used: {columns_to_send}")
    print(f"Total Input Tokens:  {total_input_tokens:,}")
    print(f"Avg Tokens/Row:      {avg_tokens_per_row:.1f}")
    print(f"Max Tokens/Row:      {max_tokens_row:,}")
    print(f"Est. Total Cost:     ${total_cost:.4f}")
    
    return total_cost

