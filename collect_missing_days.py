#!/usr/bin/env python3
"""
Script to collect missing historical weather data
"""

import sys
from datetime import datetime, date, timedelta
from database.db import Database, Location
from weather_service import WeatherAPIClient
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_missing_dates(location_id: int, start_date: date, end_date: date):
    """Find dates missing weather data for a location."""
    query = """
        SELECT DISTINCT date 
        FROM daily_weather 
        WHERE location_id = %s AND date BETWEEN %s AND %s
        ORDER BY date
    """
    existing = Database.execute_query(query, (location_id, start_date, end_date))
    existing_dates = {row['date'] for row in existing if row['date']}
    
    current = start_date
    missing = []
    while current <= end_date:
        if current not in existing_dates:
            missing.append(current)
        current += timedelta(days=1)
    
    return missing

def collect_historical_weather(location_id: int, target_date: date):
    """Collect historical weather data for a specific date."""
    location = Location.get_by_id(location_id)
    if not location:
        logger.error(f"Location {location_id} not found")
        return False
    
    # Build location query string
    location_query = f"{location.name}"
    if location.region:
        location_query += f", {location.region}"
    if location.country:
        location_query += f", {location.country}"
    
    try:
        weather_client = WeatherAPIClient()
        
        logger.info(f"Fetching historical weather for {location_query} on {target_date}")
        hist_data = weather_client.get_historical_weather(location_query, target_date)
        
        # Insert daily weather data
        query = """
            INSERT INTO daily_weather 
            (location_id, date, high_temp, low_temp, avg_temp, precipitation_mm, 
             humidity, wind_speed_kmh, wind_direction, pressure_mb, visibility_km, 
             uv_index, condition_text, condition_icon, sunrise, sunset)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                high_temp = VALUES(high_temp),
                low_temp = VALUES(low_temp),
                avg_temp = VALUES(avg_temp),
                precipitation_mm = VALUES(precipitation_mm),
                humidity = VALUES(humidity),
                wind_speed_kmh = VALUES(wind_speed_kmh),
                condition_text = VALUES(condition_text),
                condition_icon = VALUES(condition_icon),
                sunrise = VALUES(sunrise),
                sunset = VALUES(sunset)
        """
        
        # Parse sunrise/sunset times
        sunrise_time = None
        sunset_time = None
        if hist_data.get('sunrise'):
            try:
                sunrise_time = datetime.strptime(hist_data['sunrise'], '%I:%M %p').time()
            except:
                pass
        if hist_data.get('sunset'):
            try:
                sunset_time = datetime.strptime(hist_data['sunset'], '%I:%M %p').time()
            except:
                pass
        
        Database.execute_query(query, (
            location_id, target_date,
            hist_data.get('high_temp'),
            hist_data.get('low_temp'),
            hist_data.get('avg_temp'),
            hist_data.get('precipitation_mm', 0),
            hist_data.get('humidity'),
            hist_data.get('wind_speed_kmh'),
            None,  # wind_direction - not in historical data
            None,  # pressure_mb - not in historical data
            None,  # visibility_km - not in historical data
            None,  # uv_index - not in historical data
            hist_data.get('condition_text'),
            hist_data.get('condition_icon'),
            sunrise_time,
            sunset_time
        ), fetch=False)
        
        # Insert moon phase data
        moon_query = """
            INSERT INTO moon_phases 
            (location_id, date, moonrise, moonset, moon_phase, moon_illumination)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                moonrise = VALUES(moonrise),
                moonset = VALUES(moonset),
                moon_phase = VALUES(moon_phase),
                moon_illumination = VALUES(moon_illumination)
        """
        
        moonrise_time = None
        moonset_time = None
        if hist_data.get('moonrise'):
            try:
                moonrise_time = datetime.strptime(hist_data['moonrise'], '%I:%M %p').time()
            except:
                pass
        if hist_data.get('moonset'):
            try:
                moonset_time = datetime.strptime(hist_data['moonset'], '%I:%M %p').time()
            except:
                pass
        
        Database.execute_query(moon_query, (
            location_id, target_date,
            moonrise_time,
            moonset_time,
            hist_data.get('moon_phase'),
            float(hist_data.get('moon_illumination', 0)) if hist_data.get('moon_illumination') else None
        ), fetch=False)
        
        logger.info(f"✓ Successfully collected data for {location.name} on {target_date}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to collect data for {location.name} on {target_date}: {e}")
        return False

def main():
    """Main function to collect missing days."""
    # Get all locations
    locations = Location.get_all()
    
    if not locations:
        logger.error("No locations found in database")
        return
    
    # Get date range from database
    query = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM daily_weather"
    result = Database.execute_query(query)
    
    if not result or not result[0]['min_date']:
        logger.error("No existing data found to determine date range")
        return
    
    start_date = result[0]['min_date']
    end_date = result[0]['max_date']
    
    logger.info(f"Checking for missing dates between {start_date} and {end_date}")
    
    total_collected = 0
    total_failed = 0
    
    for location in locations:
        logger.info(f"\nProcessing location: {location.name}")
        missing_dates = find_missing_dates(location.id, start_date, end_date)
        
        if not missing_dates:
            logger.info(f"  No missing dates for {location.name}")
            continue
        
        logger.info(f"  Found {len(missing_dates)} missing dates: {missing_dates}")
        
        for missing_date in missing_dates:
            if collect_historical_weather(location.id, missing_date):
                total_collected += 1
            else:
                total_failed += 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Collection complete!")
    logger.info(f"  Successfully collected: {total_collected} records")
    logger.info(f"  Failed: {total_failed} records")
    logger.info(f"{'='*60}")

if __name__ == '__main__':
    main()
