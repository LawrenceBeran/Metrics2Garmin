#!/usr/local/bin/python3
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

log_dir = '/app/logs/migration.log'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)-30s%(funcName)20s():%(lineno)03s] %(message)s',
    handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(log_dir, maxBytes=1048576, backupCount=5)
    ]
)
