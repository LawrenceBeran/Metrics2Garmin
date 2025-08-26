FROM python:3.13-slim

LABEL version='0.0.1' \
      maintainer='lawrence.beran@gmail.com' \
      description='An application migrate weight metrics from Fitbit and blood pressure metrics from Omron to Garmin!'

# Set working directory
WORKDIR /app

# Install system dependencies and upgrade all packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y cron \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /etc/cron.*/*

# Copy requirements and install Python dependencies
RUN pip install --upgrade pip setuptools
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ /app/src/
COPY config/ /app/config/
COPY scripts/ /app/scripts/

RUN mkdir -p /app/data
RUN mkdir -p /app/logs

RUN ln -sf /proc/1/fd/1 /var/log/migration.log

RUN touch /app/logs/migration.log
RUN chmod oug+wr /app/logs/migration.log

# Setup volume mount point
VOLUME ["/app/data", "/app/logs"]

# Make source and scripts executable
RUN chmod +x /app/scripts/*.sh /app/src/*.py

EXPOSE 5070

# Healthcheck: calls healthcheck.py every 5 minutes
HEALTHCHECK --interval=5m --timeout=10s --start-period=1m \
  CMD python /app/src/healthcheck.py || exit 1

# Use entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]


