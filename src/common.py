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
                logger.info(f"Loaded migration state: {state}")
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