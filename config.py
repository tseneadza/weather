"""
Configuration for Weather Monitoring Application
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from the Weather directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'weather'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# WeatherAPI.com configuration
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
WEATHER_API_BASE = 'https://api.weatherapi.com/v1'

# NOAA Tides API configuration
NOAA_API_BASE = os.getenv('NOAA_API_BASE', 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter')

# Application configuration
PORT = int(os.getenv('PORT', 5105))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
