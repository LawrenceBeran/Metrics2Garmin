#!/usr/local/bin/python3
import sys
import fitbit_api as fitbit
import omron_api as omron
from base_logger import logger
import common

def main():
    try:
        
        if not common.isGarminConfigured():
            sys.exit(1)

        if common.isFitbitConfigured():
            fitbitCredentials = common.getFitbitCredentials()

            fitbit_client = fitbit.FitbitAPI(fitbitCredentials['client_id'], fitbitCredentials['client_secret'])
            if not fitbit_client.check_fitbit_profile():
                sys.exit(1)
         
        if common.isOmronConfigured():
            omronCredentials = common.getOmronCredentials()
            omron_client = omron.OmronAPI(omronCredentials['email'], omronCredentials['password'], omronCredentials['country_code'], omronCredentials['user_number'])
            if not omron_client.getUserData():
                sys.exit(1)

    except Exception as e: 
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    exit(main())