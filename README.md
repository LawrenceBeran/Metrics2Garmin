# Fitbit to Garmin Body Composition Migration and Omron to Garmin Blood Pressure Docker Container

This Docker container automatically migrates body composition data (weight, BMI, and body fat percentage) from Fitbit and blood pressure data (systolic, diastolic and pulse) from Omron to Garmin Connect on a regular schedule.

## Features

- **Automated Migration**: Runs every configurable period, in hours, via cron job
- **Comprehensive Data**: Migrates weight, BMI, and body fat percentage and blood pressure details
- **State Management**: Tracks last migration date to avoid duplicates
- **Health Monitoring**: HTTP endpoint for container information
- **Logging**: Comprehensive logging with rotation
- **Rate Limiting**: Respects API rate limits for both services

## Prerequisites

### Fitbit API Setup

1. Go to [Fitbit Developer Console](https://dev.fitbit.com/apps)
2. Create a new application
3. Note down your Client ID and Client Secret
4. Follow Fitbit's OAuth flow to obtain access and refresh tokens

### Garmin Connect Account

- Valid Garmin Connect account credentials
- Ensure your account has permission to sync the required data

## Installation

### 1. Clone or Download Files

Create a directory and save all the provided files:

```bash
mkdir metrics2garmin-migrator
cd metrics2garmin-migrator
# Save all files from the artifacts
```

### 2. Set Up Environment Variables

Copy the environment template:

```bash
cp .env.template .env
```

Edit `.env` file with your credentials:

```bash
# Fitbit API Credentials
FITBIT_CLIENT_ID=your_actual_client_id
FITBIT_CLIENT_SECRET=your_actual_client_secret

# Garmin Connect Credentials
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password

#OMRON Credentials
OMRON_EMAIL=your_omron_email@example.com
OMRON_PASSWORD=your_omron_password
OMRON_COUNTRY_CODE=your_omron_country_code # ISO two character country code
OMRON_USER_NUMBER=your_omron_user_number

SYNC_INTERVAL_HOURS=sync_period_in_hours # defaults to 6

# Optional: Timezone
TZ=Europe/London # defaults to 'UTC'
```

### 3. Create Required Directories

```bash
mkdir -p data logs
```

### 4. Build and Run

Using Docker Compose (recommended):

```bash
docker-compose up -d
```

Or using Docker directly:

```bash
docker build -t metrics2garmin-migrator .
docker run -d \
  --name metrics2garmin-migrator \
  --env-file .env \
  -p 5070:5070 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  metrics2garmin-migrator
```

## Usage

### Monitoring

The container provides a migration detail endpoint:

```bash
http://localhost:5070/
```

### Viewing Logs

View log files directly:

```bash
# Migration logs
tail -f /app/logs/migration.log
```

### Manual Migration

To trigger a manual body composition migration:

```bash
docker exec metrics2garmin-migrator python3 /app/src/metrics_migration.py
```

## Configuration

### Migration Schedule

The default schedule runs every 6 hours. To change this, modify the schedule in the `.env.` file:

```bash
SYNC_INTERVAL_HOURS=6
```

### Time Zone

Set your timezone in the `.env` file:

```bash
TZ=Europe/London 
```

## Known Limitations

The Omron API provided as part of this docker image only supports EU and North America based users, it does not support users from other regions.

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Fitbit OAuth tokens are valid and not expired
   - Check Garmin credentials are correct
   - Ensure Fitbit app has necessary permissions (weight, body fat, profile)

2. **Rate Limiting**
   - The service includes built-in rate limiting
   - Reduce migration frequency if you encounter limits

3. **Missing Data Types**
   - BMI and body fat data may not be available for all dates
   - The service will upload available data and skip missing metrics
   - Check Fitbit app to ensure you're tracking these metrics

4. **Container Health**
   - Check health endpoint: `curl http://localhost:8000/health`
   - Review logs for specific error messages

### Logs Location

- Migration logs: `app/logs/migration.log`
- Container logs: `docker logs metrics-migrator`

### Restart Service

```bash
docker-compose restart
```

## Security Considerations

- Store credentials securely using Docker secrets or encrypted environment files
- Regularly rotate API tokens
- Monitor access logs for unusual activity
- Keep the container image updated

## Data Privacy

- Body composition data (weight, BMI, body fat) is transmitted directly between Fitbit and Garmin
- No data is stored permanently in the container
- Migration state (last sync date) is stored locally

## Support

For issues with:

- **Fitbit API**: Check [Fitbit Developer Documentation](https://dev.fitbit.com/build/reference/)
- **Garmin Connect**: Verify credentials and API access
- **OMRON Connect**: Verify credentials and API access
- **Container Issues**: Check logs

## License

This project is provided as-is for personal use. Ensure compliance with both Fitbit and Garmin API terms of service.
