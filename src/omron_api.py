#!/usr/local/bin/python3

from datetime import datetime, timedelta, timezone
import requests
import hashlib
import enum
import pytz
import json
import os

from base_logger import logger


# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class DeviceCategory(enum.StrEnum):
    BPM = "0"
    SCALE = "1"
    # ACTIVITY = "2"
    # THERMOMETER = "3"
    # PULSE_OXIMETER = "4"

class OmronAPI():
    _APP_NAME = "OCM"
    _APP_URL = "/app"
    _APP_VERSION = "7.20.0"
    _USER_AGENT = f"Foresight/{_APP_VERSION} (com.omronhealthcare.omronconnect; build:37; iOS 15.8.3) Alamofire/5.9.1"
 
    _EUROPE_COUNTRY_CODES = [
            "AL", "AD", "AT", "BY", "BE", "BA", "BG", "HR", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IS", "IE", "IT", "LV", "LI", "LT",
            "LU", "MT", "MC", "ME", "NL", "MK", "NO", "PL", "PT", "RO", "RU", "SM", "RS", "SK", "SI", "ES", "SE", "CH", "UA", "GB", "VA"
            ]
    _NORTH_AMERICA_COUNTRY_CODES = ["CA", "MX", "US", "BZ", "CR", "SV", "GT", "HN", "NI", "PA"]
    
    def __init__(self, _email_address: str, _password: str, _country_code: str = 'GB', _user_number: int = -1):
        """
        Initialize the OmronAPI client.
        """
        self._email_address = _email_address
        self._password = _password
        self._country_code = _country_code
        self._user_number = int(_user_number)
        # Initialize internal values
        self._server = self.get_server(_country_code)
        self._access_token = None
        self._refresh_token = None
        self._expires_at = None
        self._lastSyncTime = 0

    def get_server(self, _country_code: str):
        """
        Get the server URL for the specified country code.
        """
        if _country_code in self._EUROPE_COUNTRY_CODES:
            return "https://oi-api.ohiomron.eu"
        elif _country_code in self._NORTH_AMERICA_COUNTRY_CODES:
            return "https://oi-api.ohiomron.com"

        # Default return north america server!
        return "https://oi-api.ohiomron.com"

    def _login(self) -> bool:
        
        if self._access_token and self._expires_at and datetime.now() < self._expires_at:
            # Access token is still valid
            logger.info("Access token is still valid")
            return True
        
        else:
            
            data = {}
            
            if not self._access_token:
                # No access token, perform login
                logger.info("No access token, performing login")
                data = {
                    "emailAddress": self._email_address,
                    "app": self._APP_NAME,
                    "country": self._country_code,
                    "password": self._password,
                }
              
            else:
                # We have an access and refresh token, need to refresh the login.
                data = {
                    "app": self._APP_NAME,
                    "emailAddress": self._email_address,
                    "refreshToken": self._refresh_token,
                }

            rawData = json.dumps(data).encode("utf-8")
            headers = {
                "user-agent": self._USER_AGENT,
                "content-type": "application/json",
                "Cache-Control": "no-cache",
                "Checksum": hashlib.sha256(rawData).hexdigest()
            }

            url = f"{self._server}{self._APP_URL}/login"
            try:
                resp = requests.post(url, data=rawData, headers=headers)
                if resp.status_code != 200:
                    logger.error(f"Login failed with status code {resp.status_code}")
                    return False
                else:
                    ret = resp.json()
                    try:
                        self._access_token = ret["accessToken"]
                        self._refresh_token = ret["refreshToken"]
                        self._expires_at = datetime.now() + timedelta(seconds=int(ret.get("expiresIn", 0)))
                        logger.info(f"Login successful with status code {resp.status_code}")
                        return True

                    except KeyError as e:
                        if resp["success"] is False:
                            logger.error(f"Login failed - interface returned: {resp['message']} {resp['errorCode']}")
                        pass

                    return None
            except requests.RequestException as err:
                print(f"An error occurred: {err}")                
            except Exception as e:
                logger.error(f"Login failed with exception {e}")
                return False

    def _getAuthHeaders(self):
        return {
            "Authorization": f"{self._access_token}"
        }

    def getUserData(self):
        """
        Fetch user data from the OMRON Connect API
        """
        if self._login() == False:
            logger.error("Login failed. Please check your credentials.")
            return None
        
        url = f"{self._server}{self._APP_URL}/user?app={self._APP_NAME}"
        resp = requests.get(url, headers=self._getAuthHeaders())
        if resp.status_code != 200:
            logger.error(f"Failed to fetch user data: {resp.status_code}")
            return None

        return resp.json()

    def getBloodPressureData(self, nextpaginationKey: int = 0, lastSyncedTime: int = 0, phoneIdentifier: str = ""):
        """
        Fetch blood pressure data from the OMRON Connect API
        """
        if self._login() == False:
            logger.error("Login failed. Please check your credentials.")
            return None
        
        _lastSyncedTime = "" if lastSyncedTime <= 0 else lastSyncedTime
        url = f"{self._server}{self._APP_URL}/v2/sync/bp?nextpaginationKey={nextpaginationKey}&lastSyncedTime={_lastSyncedTime}&phoneIdentifier={phoneIdentifier}"
        
        bpData = {}
        
        try:
            resp = requests.get(url, headers=self._getAuthHeaders())
            if resp.status_code != 200:
                logger.error(f"Failed to fetch blood pressure data: {resp.status_code}")
                return None
            else:
                logger.info(f"Fetched blood pressure data successfully: {resp.status_code}")
                bpData = resp.json()
        except requests.RequestException as err:
            logger.error(f"An error occurred: {err}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch blood pressure data: {e}")
            return None
            
        if bpData["success"] == False:
            logger.error(f"Failed to fetch blood pressure data: {bpData['message']} {bpData['errorCode']}")
            return None
            
        self._lastSyncTime = int(bpData.get("lastSyncedTime", 0))
        time = datetime.fromtimestamp(timestamp=self._lastSyncTime / 1000, tz=timezone.utc)
        
        ret = []
        
        for reading in bpData["data"]:
            try:
                if int(reading["isManualEntry"]):
                    # Skipping manual entered data
                    logger.info(f"Skipping manual entered data: {reading['timestamp']}")
                    continue
                
                if self._user_number is not None and self._user_number != -1 and self._user_number != int(reading["userNumberInDevice"]):
                    # Skipping data for a different user
                    logger.info(f"Skipping data for a different user: {reading['userNumberInDevice']}")
                    continue

                bpDataItem = {
                    "diastolicUnit": reading["diastolicUnit"],
                    "diastolic": reading["diastolic"],
                    "systolicUnit": reading["systolicUnit"],
                    "systolic": reading["systolic"],
                    "pulseUnit": reading["pulseUnit"],
                    "pulse": reading["pulse"],
                    "irregularHB": int(reading["irregularHB"]) != 0,
                    "movementDetect": int(reading["movementDetect"]) != 0,
                    "cuffWrapDetect": int(reading["cuffWrapDetect"]) != 0,
                    "notes": reading.get("notes", ""),
                    "measurementDate": datetime.fromtimestamp(timestamp=int(reading["measurementDate"]) / 1000, tz=timezone.utc),
                    "timezone": pytz.FixedOffset(int(reading["timeZone"]) // 60)
                }
                ret.append(bpDataItem)

            except KeyError as e:
                logger.exception(f"Missing mandatory key - skipping: {e}")
                continue

            except Exception as e:
                logger.exception(f"Error parsing blood pressure data - skipping: {e}")
                continue
                            
        return ret



def main():
    """Main entry point"""
    try:
        
        email_address=os.getenv('OMRON_EMAIL')
        password=os.getenv('OMRON_PASSWORD')
        country_code=os.getenv('OMRON_COUNTRY_CODE', 'GB')
        user_number=int(os.getenv('OMRON_USER_NUMBER', -1))

        omron = OmronAPI(_email_address=email_address, _password=password, _country_code=country_code, _user_number=user_number)

        userData = omron.getUserData()
        ret = omron.getBloodPressureData(nextpaginationKey=0, lastSyncedTime=0)
        
        return 0
            
    except Exception as e:
        logger.exception(f"Unexpected error during migration: {e}")
        return 1


if __name__ == "__main__":
    exit(main())