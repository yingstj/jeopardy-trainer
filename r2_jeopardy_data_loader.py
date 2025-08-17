import pandas as pd
import boto3
import io
import os
from botocore.config import Config

def get_r2_client():
    """
    Create and return a boto3 S3 client configured for Cloudflare R2.
    Uses environment variables set in Streamlit for credentials.
    """
    return boto3.client(
        's3',
        endpoint_url=os.environ.get('R2_ENDPOINT_URL', 'https://7273c297879bcf94573d10e2b8bbfc7a.r2.cloudflarestorage.com'),
        aws_access_key_id=os.environ.get('R2_ACCESS_KEY', '9c27eeaf6574bd7c80915531337fc15c'),
        aws_secret_access_key=os.environ.get('R2_SECRET_KEY', 'db3cc4453aa7ada3764653206bb43a3a4185988271d90aae277aed2eb8514050'),
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

def load_jeopardy_data_from_r2():
    """
    Load Jeopardy dataset from Cloudflare R2 storage.
    
    This version is compatible with Streamlit Cloud and 
    only uses in-memory operations with no local file caching.
    
    Returns:
        pandas.DataFrame: The loaded Jeopardy dataset
    """
    bucket_name = os.environ.get('R2_BUCKET_NAME', 'jeopardy-dataset')
    file_key = os.environ.get('R2_FILE_KEY', 'all_jeopardy_clues.csv')
    
    try:
        # Create S3 client for R2
        s3_client = get_r2_client()
        
        # Download the file from R2 directly to memory
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        
        # Read the CSV directly from the response body
        data = response['Body'].read()
        
        # Load into pandas using a BytesIO buffer
        return pd.read_csv(io.BytesIO(data))
        
    except Exception as e:
        print(f"❌ Error downloading dataset from R2: {e}")
        # Return empty DataFrame if download fails
        return pd.DataFrame()

# For development/testing outside of Streamlit Cloud
if __name__ == "__main__":
    df = load_jeopardy_data_from_r2()
    print(f"Loaded {len(df)} Jeopardy clues")
