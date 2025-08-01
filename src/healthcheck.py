#!/usr/local/bin/python3
import sys
import fitbit_api as fitbit
from base_logger import logger
import os

def main():
    try:
        # Fitbit credentials
        client_id = os.getenv('FITBIT_CLIENT_ID')
        client_secret = os.getenv('FITBIT_CLIENT_SECRET')        
        
        fitbit_client = fitbit.FitbitAPI(client_id, client_secret)
        if not fitbit_client.check_fitbit_profile():
            sys.exit(1)
    except Exception as e: 
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    exit(main())