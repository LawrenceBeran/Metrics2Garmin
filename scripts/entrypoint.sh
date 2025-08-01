#!/bin/bash
set -e

echo "Starting Body Composition Migration Service..."

# Load env vars
#export $(grep -v '^#' .env | xargs)

# Load environment variables into /etc/environment for cron jobs.
env >> /etc/environment

# Replace token in crontab template
sed "s/{{SYNC_INTERVAL_HOURS}}/${SYNC_INTERVAL_HOURS:-6}/" /app/config/crontab.template > /etc/cron.d/metrics-sync

# Give execution rights and run to the cron job
chmod 0644 /etc/cron.d/metrics-sync
crontab /etc/cron.d/metrics-sync

# Run initial body composition migration
echo "Running initial body composition migration..."
/app/src/metrics_migration.py

# Start cron daemon
echo "Starting cron with ${SYNC_INTERVAL_HOURS:-6} hour interval..."
cron

echo "Starting Flask..."
/app/src/routes.py
