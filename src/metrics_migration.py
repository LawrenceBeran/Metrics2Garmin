#!/usr/local/bin/python3
"""
Body Composition Migration - Fitbit to Garmin
Migrates weight, BMI, and body fat percentage data from Fitbit to Garmin Connect
"""

import debugpy
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import time
from dateutil.parser import parse
from garminconnect import Garmin
from dotenv import load_dotenv

import omron_api as omron
import fitbit_api as fitbit
from base_logger import logger
from common import MIGRATION_TYPE
import common

# Load environment variables
load_dotenv()


# Enable debugging if specified in environment variables
debug = os.getenv('DEBUG', 'false').lower() in ('true', '1', 't')
if debug:
    debugpy.listen(('0.0.0.0', 5678))
#    debugpy.wait_for_client()
    logger.info("Debugging (not) enabled")


class BodyCompositionMigrator:
    def __init__(self):
        self.setup_credentials()
        self._garmin_client = None
        self._fitbit_client = None
        self._omron_client = None

       
    def setup_credentials(self):
        # Garmin credentials
        self.garmin_email = os.getenv('GARMIN_EMAIL')
        self.garmin_password = os.getenv('GARMIN_PASSWORD')
  
        required_vars = ['GARMIN_EMAIL', 'GARMIN_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    
    def connect_garmin(self):
        """Initialize Garmin client"""
        try:
            self._garmin_client = Garmin(self.garmin_email, self.garmin_password)
            self._garmin_client.login()
            logger.info("Successfully connected to Garmin")
            return True
        except Exception as e:
            logger.exception(f"Failed to connect to Garmin: {e}")
            return False


    def isFitbitConfigured(self) -> bool:
        """Check if Fitbit credentials are configured"""
        client_id = os.getenv('FITBIT_CLIENT_ID')
        client_secret = os.getenv('FITBIT_CLIENT_SECRET')
        return bool(client_id and client_secret)
    
    
    def connect_fitbit(self) -> bool:
        """Initialize Fitbit client"""
        try:
            client_id = os.getenv('FITBIT_CLIENT_ID')
            client_secret = os.getenv('FITBIT_CLIENT_SECRET')

            required_vars = ['FITBIT_CLIENT_ID', 'FITBIT_CLIENT_SECRET']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

            self._fitbit_client = fitbit.FitbitAPI(client_id, client_secret)
            if not self._fitbit_client.check_fitbit_profile():
                logger.error("Failed to connect to Fitbit: Invalid profile")
                return False
            logger.info("Successfully connected to Fitbit")
            return True
        except Exception as e:
            logger.exception(f"Failed to connect to Fitbit: {e}")
            return False


    def isOmronConfigured(self) -> bool:
        """Check if Omron credentials are configured"""
        email_address = os.getenv('OMRON_EMAIL')
        password = os.getenv('OMRON_PASSWORD')
        country_code = os.getenv('OMRON_COUNTRY_CODE')
        return bool(email_address and password and country_code)


    def connect_omron(self) -> bool:
        """Initialize Omron client"""
        try:
            email_address=os.getenv('OMRON_EMAIL')
            password=os.getenv('OMRON_PASSWORD')
            country_code=os.getenv('OMRON_COUNTRY_CODE')
            user_number=int(os.getenv('OMRON_USER_NUMBER', -1))
            
            required_vars = ['OMRON_EMAIL', 'OMRON_PASSWORD', 'OMRON_COUNTRY_CODE']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")            
            
            self._omron_client = omron.OmronAPI(_email_address=email_address, _password=password, _country_code=country_code, _user_number=user_number)
            if not self._omron_client._login():
                logger.error("Failed to connect to Omron: Invalid credentials")
                return False
            
            logger.info("Successfully connected to Omron")
            return True
        
        except Exception as e:
            logger.exception(f"Failed to connect to Omron: {e}")
            return False

    def get_fitbit_body_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch body composition data from Fitbit (weight, BMI, body fat)"""
        try:
            body_data = self._fitbit_client.get_fitbit_body_data(start_date, end_date)
            logger.info(f"Retrieved {len(body_data)} body composition entries from Fitbit")
            return body_data
            
        except Exception as e:
            logger.exception(f"Error fetching Fitbit body data: {e}")
            return []


    def trim_allready_existing_bp_data(self, _gc_bp_data: List[Dict], _omron_bp_data: List[Dict]) -> List[Dict]:
        """Remove allready existing data from the list of body composition data"""
        logger.info(f"Reviewing Omron blood pressure measurements and removing any that already exist in Garmin!")
        trimmed_data = []
        for entry in _omron_bp_data:
            entry_datetime = common.get_datetime_from_entry(entry)
            if not any(gcMeasurement['measurementTimestamp'] == entry_datetime.timestamp() for gcMeasurement in _gc_bp_data):
                trimmed_data.append(entry)
        logger.info(f"Trimmed {len(_omron_bp_data) - len(trimmed_data)} blood pressure entries from Omron data!")
        return trimmed_data
    

    def upload_blood_pressure_data_to_garmin(self, blood_pressure_data: List[Dict]) -> int:
        """Upload blood pressure data to Garmin Connect"""
        successful_uploads = 0
     
        for entry in blood_pressure_data:
            try:
                entry_datetime = common.get_datetime_from_entry(entry)
                timestamp = entry_datetime.isoformat() 

                # Prepare body composition data
                bp = {}
                    
                if entry.get('systolic'):
                    bp['systolic'] = int(entry['systolic'])

                if entry.get('diastolic'):
                    bp['diastolic'] = int(entry['diastolic'])

                if entry.get('pulse'):
                    bp['pulse'] = int(entry['pulse'])

                notes = entry.get('notes', '')
                if entry.get('movementDetect', False):
                    notes = f"{notes}, Body Movement detected"
                if entry.get('irregularHB', False):
                    notes = f"{notes}, Irregular heartbeat detected"
                if not entry.get('cuffWrapDetect', True):
                    notes = f"{notes}, Cuff wrap error"
                    
                if notes:
                    notes = notes.lstrip(", ")
                    bp['notes'] = notes
                
                # Upload to Garmin using the blood pressure method
                result = self._garmin_client.set_blood_pressure(
                        timestamp=timestamp
                    ,   **bp
                )
                
                if result:
                    successful_uploads += 1
                    metrics = []
                    if entry.get('systolic'):
                        metrics.append(f"systolic: {entry['systolic']}{entry['systolicUnit']}")
                    if entry.get('diastolic'):
                        metrics.append(f"diastolic: {entry['diastolic']}{entry['diastolicUnit']}")
                    if entry.get('pulse'):
                        metrics.append(f"pulse: {entry['pulse']}{entry['pulseUnit']}")
                    if entry.get('notes'):
                        metrics.append(f"Notes: {notes}")
                    
                    logger.info(f"Successfully uploaded {', '.join(metrics)} for {timestamp}")
                else:
                    logger.warning(f"Failed to upload body data for {timestamp}")
                        
                time.sleep(0.2)  # Rate limiting            
                
            except Exception as e:
                logger.exception(f"Error uploading body composition entry {entry}: {e}")
        
        return successful_uploads
    

    def upload_body_comp_data_to_garmin(self, body_data: List[Dict]) -> int:
        """Upload body composition data to Garmin Connect"""
        successful_uploads = 0
        
        for entry in body_data:
            try:
                # Skip entries with no data
                if not any([entry.get('weight'), entry.get('bmi'), entry.get('body_fat')]):
                    continue
                
                entry_datetime = common.get_datetime_from_entry(entry)
                timestamp = entry_datetime.isoformat() 
                
                # Prepare body composition data
                body_composition = {}
                
                if entry.get('weight'):
                    body_composition['weight'] = float(entry['weight'])
                
                if entry.get('bmi'):
                    body_composition['bmi'] = float(entry['bmi'])
                
                if entry.get('body_fat'):
                    body_composition['percent_fat'] = float(entry['body_fat'])
                
                # Upload to Garmin using the body composition method
                result = self._garmin_client.add_body_composition(
                    timestamp=timestamp,
                    **body_composition
                )
                
                if result:
                    successful_uploads += 1
                    metrics = []
                    if entry.get('weight'):
                        metrics.append(f"weight: {entry['weight']}kg")
                    if entry.get('bmi'):
                        metrics.append(f"BMI: {entry['bmi']}")
                    if entry.get('body_fat'):
                        metrics.append(f"body fat: {entry['body_fat']}%")
                    
                    logger.info(f"Successfully uploaded {', '.join(metrics)} for {timestamp}")
                else:
                    logger.warning(f"Failed to upload body data for {timestamp}")
                        
                time.sleep(0.2)  # Rate limiting
                
            except Exception as e:
                logger.exception(f"Error uploading body composition entry {entry}: {e}")
        
        return successful_uploads

    def get_garmin_bp_measurements(self, _from_date: datetime, _to_date: datetime):
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


    def get_latest_recorded_date(self, p_data) -> Optional[datetime]:
        """Get the latest recorded date from the provided data"""
        if not p_data:
            return None

        item = max(p_data, key=common.get_datetime_from_entry)

        return common.get_datetime_from_entry(item)


    def fitbit2garmin_migrate_body_composition(self):
        """Main migration function for body composition data"""
        logger.info("Starting Fitbit2garmin weight data migration process")
        
        # Connect to both services
        if not self.connect_fitbit():
            logger.error("Failed to connect to Fitbit. Aborting migration.")
            return False
        
        if not self.connect_garmin():
            logger.error("Failed to connect to Garmin. Aborting migration.")
            return False
        
        # Get date range for migration
        start_date = common.get_last_migration_date(MIGRATION_TYPE.FITBIT)
        if start_date is None:
            start_date = datetime(2000, 1, 1)
        end_date = datetime.now()
        
        logger.info(f"Migrating body composition data from {start_date.date()} to {end_date.date()}")
        
        # Fetch body composition data from Fitbit
        body_data = self.get_fitbit_body_data(start_date, end_date)
        
        if not body_data:
            logger.info("No body composition data found to migrate")
            return True
        
        # Log summary of data found
        weight_count = sum(1 for entry in body_data if entry.get('weight'))
        bmi_count = sum(1 for entry in body_data if entry.get('bmi'))
        fat_count = sum(1 for entry in body_data if entry.get('body_fat'))
        
        logger.info(f"Found: {weight_count} weight entries, {bmi_count} BMI entries, {fat_count} body fat entries")
        
        # Upload to Garmin
        successful_uploads = self.upload_body_comp_data_to_garmin(body_data)
        
        logger.info(f"Migration completed: {successful_uploads}/{len(body_data)} entries uploaded successfully")
        
        # Save migration state

        # Update the end_date to the last recorded date in the data. If no data provided, use the start_date.
        last_recorded_date = self.get_latest_recorded_date(body_data)
        if last_recorded_date:
            end_date = last_recorded_date
        else:
            end_date = start_date

        common.save_migration_state(MIGRATION_TYPE.FITBIT, end_date)

        return successful_uploads > 0

    def omron2garmin_migrate_blood_pressure(self):
        """Main migration function for blood pressure data"""
        logger.info("Starting blood pressure migration process")

        # Connect to both services
        if not self.connect_omron():
            logger.error("Failed to connect to Omron. Aborting migration.")
            return False

        if not self.connect_garmin():
            logger.error("Failed to connect to Garmin. Aborting migration.")
            return False

        # Get date range for migration
        start_date = common.get_last_migration_date(MIGRATION_TYPE.OMRON)
        if start_date is None:
            start_date = datetime.fromtimestamp(timestamp=0, tz=timezone.utc)
        end_date = datetime.now()

        logger.info(f"Migrating blood pressure data from {start_date.date()} to {end_date.date()}")

        # omronUD = self._omron_client.getUserData()
        # TODO - get the TZ from here... Could use the connection country_code to determine the timezone as well!

        # Fetch blood pressure data from Omron
        omron_bp_data = self._omron_client.getBloodPressureData(lastSyncedTime=int(start_date.timestamp())*1000)

        if not omron_bp_data:
            logger.info("No blood pressure data found to migrate")
            return True

        # Get the last recorded datetime from the read metrics
        last_recorded_date = self.get_latest_recorded_date(omron_bp_data)

        gc_pb_data = self.get_garmin_bp_measurements(start_date, end_date)
        if gc_pb_data:
            omron_bp_data = self.trim_allready_existing_bp_data(_gc_bp_data=gc_pb_data, _omron_bp_data=omron_bp_data)

        if not omron_bp_data:
            logger.info("No blood pressure data found to migrate")
            if gc_pb_data:
                # Save migration state
                common.save_migration_state(MIGRATION_TYPE.OMRON, last_recorded_date)
            return True

        # Log summary of data found
        logger.info(f"Found: {len(omron_bp_data)} blood pressure entries")

        # Upload to Garmin
        successful_uploads = self.upload_blood_pressure_data_to_garmin(omron_bp_data)

        logger.info(f"Migration completed: {successful_uploads}/{len(omron_bp_data)} entries uploaded successfully")

        # Update the end_date to the last recorded date in the data. If no data provided, use the start_date.
        if last_recorded_date:
            end_date = last_recorded_date
        else:
            end_date = start_date

        # Save migration state
        common.save_migration_state(MIGRATION_TYPE.OMRON, end_date)

        return successful_uploads > 0


def main():
    """Main entry point"""
    try:
        migrator = BodyCompositionMigrator()

        if migrator.isFitbitConfigured():
            success = migrator.fitbit2garmin_migrate_body_composition()
            if success:
                logger.info("Fitbit2Garmin Body composition migration completed successfully")
            else:
                logger.error("Fitbit2Garmin Body composition migration failed")

        if migrator.isOmronConfigured():
            success = migrator.omron2garmin_migrate_blood_pressure()
            if success:
                logger.info("Omron2Garmin blood pressure migration completed successfully")
            else:
                logger.error("Omron2Garmin blood pressure migration failed")

        return 0
            
    except Exception as e:
        logger.exception(f"Unexpected error during migration: {e}")
        return 1


if __name__ == "__main__":
    exit(main())