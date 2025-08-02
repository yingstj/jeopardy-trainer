#!/usr/bin/env python3
"""Get the correct DATABASE_URL from Railway"""
import subprocess
import json

print("Fetching PostgreSQL credentials from Railway...\n")

# Get all services
result = subprocess.run(["railway", "service", "list", "--json"], capture_output=True, text=True)
if result.returncode == 0:
    services = json.loads(result.stdout)
    print("Services in your project:")
    for service in services:
        print(f"  - {service['name']}")
    print("\nTo get the correct DATABASE_URL:")
    print("1. Go to https://railway.app/dashboard")
    print("2. Click on your Jay Jeopardy AI Trainer project")
    print("3. Click on the Postgres service (not the volume)")
    print("4. Click on the 'Variables' tab")
    print("5. Copy the entire DATABASE_URL value")
    print("6. Update it in your Jay Jeopardy AI Trainer service variables")
else:
    print("Please run this from the linked project directory")