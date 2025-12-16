"""Test script to verify .env loading"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / '.env'
print(f"Loading .env from: {env_path}")
print(f".env exists: {env_path.exists()}")

load_dotenv(env_path)

# Check all N8N variables
print("\n=== N8N Variables ===")
print(f"N8N_URL: {os.getenv('N8N_URL')}")
print(f"N8N_USERNAME: {os.getenv('N8N_USERNAME')}")
print(f"N8N_PASSWORD: {os.getenv('N8N_PASSWORD')[:10]}..." if os.getenv('N8N_PASSWORD') else "N8N_PASSWORD: NOT SET")
print(f"N8N_API_KEY: {os.getenv('N8N_API_KEY')[:20]}..." if os.getenv('N8N_API_KEY') else "N8N_API_KEY: NOT SET")

# Test N8N connection
print("\n=== Testing N8N Connection ===")
import requests

api_key = os.getenv('N8N_API_KEY')
if api_key:
    headers = {'X-N8N-API-KEY': api_key}
    try:
        response = requests.get('https://n8n.kleberodrigues.shop/api/v1/workflows', headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            workflows = data.get('data', [])
            print(f"Workflows found: {len(workflows)}")
            for wf in workflows[:3]:
                print(f"  - {wf['name']} (ID: {wf['id']}, Active: {wf['active']})")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("N8N_API_KEY not found in environment!")
