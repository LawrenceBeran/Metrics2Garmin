#!/usr/local/bin/python3
from typing import Dict
from base_logger import logger
from dateutil.parser import parse
from datetime import datetime, timedelta, date
from enum import Enum
import os
import json


def get_datetime_from_entry(entry: Dict) -> datetime:
    """Extract datetime from entry dictionary"""
    if 'date' in entry:
        try:
            # Create datetime object
            entry_date = parse(entry['date'])
            entry_time = entry.get('time', '08:00:00')
            
            # Parse time and combine with date
            time_parts = entry_time.split(':')
            entry_datetime = entry_date.replace(
                hour=int(time_parts[0]),
                minute=int(time_parts[1]),
                second=int(time_parts[2]) if len(time_parts) > 2 else 0
            )

            return entry_datetime

        except ValueError as e:
            logger.error(f"Invalid date/time format in entry {entry}: {e}")
            return datetime.min
        
    if 'measurementDate' in entry:
        return entry['measurementDate']
        
    return datetime.min


STATE_FILE = '/app/data/migration_state.json'
VERSION_FILE = '/app/src/version.txt'
DEFAULT_DAYS = 30

class MIGRATION_TYPE(Enum):
    FITBIT = 1
    GOOGLE_FIT = 2
    OMRON = 3

def get_version() -> str:
    """Get the version of the application"""
    try:
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    except Exception as e:
        logger.exception(f"Error reading version file: {e}")
        return '0.0.0'

def get_migration_state() -> Dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                logger.info(f"Loaded migration state file!")
                return state
    except Exception as e:
        logger.exception(f"Error reading state file {STATE_FILE}: {e}")
        
    return None

def get_last_migration_date(p_item: MIGRATION_TYPE) -> datetime:
    """Get the last migration date from state file"""
    
    state = get_migration_state() or {}
    try:
        _dateValue = None
        if p_item == MIGRATION_TYPE.FITBIT:
            # For Fitbit, use the last migration date
            _dateValue = state.get('last_fitbit_migration_date', None)
        elif p_item == MIGRATION_TYPE.GOOGLE_FIT:
            _dateValue = state.get('last_google_fit_migration_date', None)
        elif p_item == MIGRATION_TYPE.OMRON:
            _dateValue = state.get('last_omron_migration_date', None)

        if _dateValue is not None:
            return parse(_dateValue)

        return None
    
    except Exception as e:
        logger.exception(f"Error reading state file {STATE_FILE}: {e}")

    return None


def save_migration_state(p_item: MIGRATION_TYPE, last_date: datetime):
    """Save the last migration date to state file"""
    
    state = get_migration_state() or {}
    if p_item == MIGRATION_TYPE.FITBIT:
        state['last_fitbit_migration_date'] = last_date.isoformat()
    elif p_item == MIGRATION_TYPE.GOOGLE_FIT:
        state['last_google_fit_migration_date'] = last_date.isoformat()
    elif p_item == MIGRATION_TYPE.OMRON:
        state['last_omron_migration_date'] = last_date.isoformat()

    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
        logger.info(f"Saved migration state: {p_item} {last_date}")
    except Exception as e:
        logger.exception(f"Error saving state file {STATE_FILE}: {e}")


def isFitbitConfigured() -> bool:
    """Check if Fitbit credentials are configured"""
    client_id = os.getenv('FITBIT_CLIENT_ID')
    client_secret = os.getenv('FITBIT_CLIENT_SECRET')
    # TODO - add the check to ensure the token file exists as well!
    return bool(client_id and client_secret)

def getFitbitCredentials() -> Dict:
    return {
            'client_id': os.getenv('FITBIT_CLIENT_ID') if os.getenv('FITBIT_CLIENT_ID') else None,
            'client_secret': os.getenv('FITBIT_CLIENT_SECRET') if os.getenv('FITBIT_CLIENT_SECRET') else None
        }

def isGarminConfigured() -> bool:
    """Check if Garmin credentials are configured"""
    email = os.getenv('GARMIN_EMAIL')
    password = os.getenv('GARMIN_PASSWORD')
    return bool(email and password)

def getGarminCredentials() -> Dict:
    return {
            'email': os.getenv('GARMIN_EMAIL') if os.getenv('GARMIN_EMAIL') else None,
            'password': os.getenv('GARMIN_PASSWORD') if os.getenv('GARMIN_PASSWORD') else None
        }

def isOmronConfigured() -> bool:
    """Check if Omron credentials are configured"""
    email_address = os.getenv('OMRON_EMAIL')
    password = os.getenv('OMRON_PASSWORD')
    country_code = os.getenv('OMRON_COUNTRY_CODE')
    return bool(email_address and password and country_code)

def getOmronCredentials() -> Dict:
    return {
            'email': os.getenv('OMRON_EMAIL') if os.getenv('OMRON_EMAIL') else None,
            'password': os.getenv('OMRON_PASSWORD') if os.getenv('OMRON_PASSWORD') else None,
            'country_code': os.getenv('OMRON_COUNTRY_CODE') if os.getenv('OMRON_COUNTRY_CODE') else None,
            'user_number': os.getenv('OMRON_USER_NUMBER') if os.getenv('OMRON_USER_NUMBER') else -1
        }
