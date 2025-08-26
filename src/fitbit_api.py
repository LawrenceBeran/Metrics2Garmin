#!/usr/local/bin/python3
from datetime import datetime, timedelta
import requests
import json
import time

from base_logger import logger  
import common


FITBIT_BASE = "https://api.fitbit.com"
TOKEN_FILE = "/app/data/fitbit_tokens.json"

class FitbitAPI:
    def __init__(self, _client_id: str, _client_secret: str):
        self.setup_credentials(_client_id, _client_secret)

    def setup_credentials(self, _client_id: str, _client_secret: str):
        self.client_id = _client_id
        self.client_secret = _client_secret
        if not self.client_id or not self.client_secret:
            logger.error("Fitbit clientId and client secret must be provided.")
            raise ValueError("Fitbit clientId and client secret must be provided.")

        tokens = self.load_tokens()
        self.access_token = tokens.get('access_token')
        self.refresh_token = tokens.get('refresh_token')

        required_vars = ['access_token', 'refresh_token']
        missing_vars = [var for var in required_vars if not tokens.get(var)]
        if missing_vars:
            logger.error(f"Missing required configuration variables from {TOKEN_FILE}: {', '.join(missing_vars)}")
            raise ValueError(f"Missing required configuration variables from {TOKEN_FILE}: {', '.join(missing_vars)}")


    def load_tokens(self):
        try:
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
            logger.info(f"Successfully loaded tokens from {TOKEN_FILE}")
        except Exception as e:
            logger.exception(f"Failed to load token file: {TOKEN_FILE}. Please ensure it exists and is valid JSON. {e}")


    def save_tokens(self, tokens):
        try:
            with open(TOKEN_FILE, "w") as f:
                json.dump(tokens, f)
                logger.info(f"Successfully saved tokens to {TOKEN_FILE}")
        except Exception as e:
            logger.exception(f"Failed to save tokens to {TOKEN_FILE}. Please check file permissions and path. {e}")

        
    def refresh_fitbit_token(self):
        response = requests.post(
            f"{FITBIT_BASE}/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
            },
            auth=(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

        new_tokens = response.json()

        self.save_tokens(new_tokens)
        
        self.access_token = new_tokens.get("access_token")
        self.refresh_token = new_tokens.get("refresh_token")

        return new_tokens["access_token"]


    def get_fitbit_access_token(self):
        return self.access_token or self.refresh_fitbit_token()


    def handle_fitbit_rate_limits(self, response) -> bool:
        if response.status_code == 429:
            reset_time = int(response.headers.get("fitbit-rate-limit-reset", 60))
            logger.info(f"Rate limit hit. Sleeping for {reset_time} seconds.")
            time.sleep(reset_time)
            return True
        return False


    def get_fitbit_body_data(self, p_start_date: datetime, p_end_date: datetime):
        current_date = p_start_date
        p_end_date = p_end_date
        all_data = []

        while current_date < p_end_date:
            end_date = (current_date + timedelta(days=30))
            if end_date > p_end_date:
                end_date = p_end_date

            start_str = current_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            token = self.get_fitbit_access_token()
            url = f"{FITBIT_BASE}/1/user/-/body/log/weight/date/{start_str}/{end_str}.json"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers)

            if response.status_code == 401:
                token = self.refresh_fitbit_token()
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(url, headers=headers)

            if self.handle_fitbit_rate_limits(response):
                continue

            if response.status_code != 200:
                logger.error(f"Failed on {start_str}:{end_str}: {response.status_code} - {response.text}")
                current_date += timedelta(days=1)
                continue

            data = response.json().get("weight", [])
            if data:
                all_data.extend(data)
                
            time.sleep(0.5)  # polite delay
            current_date += timedelta(days=30)

        # Process the data to ensure it is in the correct format
        ret_data = []
        for entry in all_data: 
            
            # Only add entries where the entry's date time objects are after the last migration date/time 
            if common.get_datetime_from_entry(entry) <= p_start_date:
                logger.debug(f"Skipping entry {entry} as it is before the start date {p_start_date}")
                continue
            
            if entry.get('body_fat'):
                body_fat = round(entry['body_fat'], 2)
            elif entry.get('fat'):
                body_fat = round(entry['fat'], 2)
            else:
                body_fat = None
            
            ret_entry = {
                "date": entry["date"],
                "time": entry.get("time", "08:00:00"),
                "weight": round(entry["weight"], 2),
                "bmi": round(entry.get("bmi", 0), 2),
                "body_fat": body_fat,
            }
            
            ret_data.append(ret_entry)

        return ret_data


    def check_fitbit_profile(self) -> bool:

        url = f"{FITBIT_BASE}/1/user/-/profile.json"
        token = self.get_fitbit_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)

        if response.status_code == 401:
            token = self.refresh_fitbit_token()
            headers["Authorization"] = f"Bearer {token}"
            response = requests.get(url, headers=headers)

        if self.handle_fitbit_rate_limits(response):
            response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return True
        
        logger.error(f"Unexpected status: {response.status_code}")
        return False