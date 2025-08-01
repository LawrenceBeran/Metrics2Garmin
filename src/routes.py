#!/usr/bin/env python3

from flask import Flask
from common import MIGRATION_TYPE
import common

app = Flask(__name__)


@app.route('/')
def home():
    last_fitbit_migration_date = common.get_last_migration_date(MIGRATION_TYPE.FITBIT)
    last_omron_migration_date = common.get_last_migration_date(MIGRATION_TYPE.GOOGLE_FIT)
    
    
    return f'<h1>Hello from Flask & Docker</h1>' \
           f'<p>Last Fitbit metric migrated: {last_fitbit_migration_date.strftime("%x %X") if last_fitbit_migration_date else "Never"}</p>' \
           f'<p>Last Omron metric migrated: {last_omron_migration_date.strftime("%x %X") if last_omron_migration_date else "Never"}</p>' \



def main():
    """Main entry point"""
    app.run(host='0.0.0.0', port='5070', debug=True)

if __name__ == "__main__":
    exit(main())