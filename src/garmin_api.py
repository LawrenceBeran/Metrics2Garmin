#!/usr/local/bin/python3
from datetime import datetime, timedelta
from garth.exc import GarthHTTPError
import json

from base_logger import logger  

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
)



TOKEN_FILE = "/app/data/garmin_tokens"

class GarminAPI:
    def __init__(self, _email: str, _password: str):
        self._garmin_client = None
        self.setup_credentials(_email, _password)

    def setup_credentials(self, _email: str, _password: str):
        self._email = _email
        self._password = _password
        if not self._email or not self._password:
            logger.error("Garmin email and password must be provided.")
            raise ValueError("Garmin email and password must be provided.")


    def load_tokens(self):
        try:
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
            logger.info(f"Successfully loaded tokens from {TOKEN_FILE}")
        except FileNotFoundError:
            logger.debug(f"Token file {TOKEN_FILE} not found.")
        except Exception as e:
            logger.exception(f"Failed to load token file: {TOKEN_FILE}. Please ensure it exists and is valid JSON. {e}")   
        return None

    def save_tokens(self, tokens) -> bool:
        try:
            with open(TOKEN_FILE, "w") as f:
                json.dump(tokens, f)
                logger.info(f"Successfully saved tokens to {TOKEN_FILE}")
        except Exception as e:
            logger.exception(f"Failed to save tokens to {TOKEN_FILE}. Please check file permissions and path. {e}")
        else:
            return True
        return False

    def login(self) -> bool:
        try:
            # Try to connect using (possibly) cached OAuth2 tokens
            tokens = self.load_tokens()
            if tokens:
                self._garmin_client = Garmin()
                self._garmin_client.login(tokens)
                return True
            else:
                raise FileNotFoundError()

        except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
            # Session is expired or tokens do not exist. You'll need to log in again
            
            try:
                self._garmin_client = Garmin(self._email, self._password)    
                result1, result2 = self._garmin_client.login()
                
                if result1 == "needs_mfa":
                    logger.error("Garmin login failed: MFA required.")
                    
                # Encode Oauth1 and Oauth2 tokens to base64 string and safe to file for next login (alternative way)
                tokens = self._garmin_client.garth.dumps()
                self.save_tokens(tokens)
                
                 # Re-login Garmin API with tokens
                self._garmin_client.login(tokens)

                return True

            except Exception as e:
                logger.exception(f"Garmin login failed: {e}")

        return False

    def set_blood_pressure(self, p_systolic: int, p_diastolic: int, p_pulse: int, p_timestamp: datetime, p_notes: str) -> bool:
        try:
            timestamp = p_timestamp.isoformat()

            results = self._garmin_client.set_blood_pressure(systolic=p_systolic, diastolic=p_diastolic, pulse=p_pulse, timestamp=timestamp, notes=p_notes)
            
            if results:
                metrics = []
                if p_systolic:
                    metrics.append(f"systolic: {p_systolic}")
                if p_diastolic:
                    metrics.append(f"diastolic: {p_diastolic}")
                if p_pulse:
                    metrics.append(f"pulse: {p_pulse}")
                if p_notes:
                    metrics.append(f"Notes: {p_notes}")

                logger.info(f"Successfully uploaded {', '.join(metrics)} for {timestamp}")
                return True
                
            else:
                logger.warning(f"Failed to upload body data for {timestamp}")            

            logger.info(f"Successfully set blood pressure to {p_systolic}/{p_diastolic} at {p_timestamp}")
            
        except Exception as e:
            logger.exception(f"Failed to set blood pressure: {e}")
            
        return False
    
    def get_blood_pressure_measurements(self, _from_date: datetime, _to_date: datetime):
        # search dates are in local time
        fromDate = _from_date.isoformat(timespec="seconds")
        toDate = _to_date.isoformat(timespec="seconds")
        
        gcData = self._garmin_client.get_blood_pressure(startdate=fromDate, enddate=toDate)
        
        # reduce to list of measurements
        _gcMeasurements = [metric for x in gcData["measurementSummaries"] for metric in x["measurements"]]        
        
        # map of garmin-key:omron-key
        gcMeasurements = []
        for metric in _gcMeasurements:
            # use UTC for comparison
            dtUTC = datetime.fromisoformat(f"{metric['measurementTimestampGMT']}Z")
            gcMeasurements.append({
                "systolic": metric["systolic"],
                "diastolic": metric["diastolic"],
                "pulse": metric["pulse"],
                "measurementTimestamp": dtUTC.timestamp()
            })
        
        return gcMeasurements
    
    def add_body_composition(self, p_timestamp: datetime, p_weight: float, p_bmi: float = None, p_body_fat: float = None) -> int:
        try:
            timestamp = p_timestamp.isoformat()             
            # Upload to Garmin using the body composition method
            result = self._garmin_client.add_body_composition(weight=p_weight, bmi=p_bmi, percent_fat=p_body_fat, timestamp=timestamp)
            
            if result:
                metrics = []
                if p_weight:
                    metrics.append(f"weight: {p_weight}kg")
                if p_bmi:
                    metrics.append(f"BMI: {p_bmi}")
                if p_body_fat:
                    metrics.append(f"body fat: {p_body_fat}%")
                
                logger.info(f"Successfully uploaded {', '.join(metrics)} for {timestamp}")
                
                return True

            else:
                logger.warning(f"Failed to upload body data for {timestamp}")
                
        except Exception as e:
            logger.exception(f"Error uploading body composition entry {timestamp}: {e}")

        return False