#!/usr/bin/env python3
"""
Weather Monitoring App - Flask Application
Monitors weather conditions, collects daily data, and provides forecasts
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, date, timedelta
import logging
from typing import Dict, Optional

from database.db import Database, Location, check_daily_weather_collected
from weather_service import WeatherAPIClient
from tides_service import NOAATidesClient
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize API clients
weather_client = WeatherAPIClient()
tides_client = NOAATidesClient()


def collect_daily_weather(location_id: int, force: bool = False) -> Dict:
    """
    Collect daily weather data for a location if not already collected today.
    
    Args:
        location_id: Location ID
        force: Force collection even if already collected today
        
    Returns:
        Dictionary with collection status and data
    """
    location = Location.get_by_id(location_id)
    if not location:
        return {'success': False, 'error': 'Location not found'}
    
    today = datetime.now().date()
    
    # Check if already collected
    if not force and check_daily_weather_collected(location_id, today):
        logger.info(f"Weather data already collected for location {location_id} on {today}")
        return {'success': True, 'message': 'Already collected', 'collected': False}
    
    try:
        # Build location query string
        location_query = f"{location.name}"
        if location.region:
            location_query += f", {location.region}"
        if location.country:
            location_query += f", {location.country}"
        
        # Get forecast data first (to get today's high/low temps)
        logger.info(f"Fetching forecast data for {location_query}")
        forecast_data = weather_client.get_forecast(location_query, days=1)
        
        loc_data = forecast_data['location']
        today_forecast = forecast_data['forecasts'][0] if forecast_data.get('forecasts') else None
        
        # Get current weather for additional details
        logger.info(f"Fetching current weather data for {location_query}")
        weather_data = weather_client.get_current_weather(location_query)
        current = weather_data['current']
        
        # Update location if coordinates are missing
        if not location.latitude and loc_data.get('latitude'):
            query = "UPDATE locations SET latitude = %s, longitude = %s, timezone = %s WHERE id = %s"
            Database.execute_query(query, (
                loc_data['latitude'],
                loc_data['longitude'],
                loc_data.get('timezone'),
                location_id
            ), fetch=False)
        
        # Use forecast data for high/low temps, current weather for other details
        high_temp = today_forecast.get('high_temp') if today_forecast else current.get('temp_c')
        low_temp = today_forecast.get('low_temp') if today_forecast else current.get('temp_c')
        avg_temp = current.get('temp_c')
        precip_mm = today_forecast.get('precipitation_mm', 0) if today_forecast else current.get('precip_mm', 0)
        condition_text = current.get('condition')
        condition_icon = current.get('condition_icon')
        
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
                wind_direction = VALUES(wind_direction),
                pressure_mb = VALUES(pressure_mb),
                visibility_km = VALUES(visibility_km),
                uv_index = VALUES(uv_index),
                condition_text = VALUES(condition_text),
                condition_icon = VALUES(condition_icon),
                sunrise = VALUES(sunrise),
                sunset = VALUES(sunset)
        """
        
        Database.execute_query(query, (
            location_id, today,
            high_temp,
            low_temp,
            avg_temp,
            precip_mm,
            current.get('humidity'),
            current.get('wind_kph'),
            current.get('wind_dir'),
            current.get('pressure_mb'),
            current.get('visibility_km'),
            current.get('uv'),
            condition_text,
            condition_icon,
            None,  # sunrise - will get from astronomy
            None   # sunset - will get from astronomy
        ), fetch=False)
        
        # Get astronomy data (moon phases, sunrise/sunset)
        logger.info(f"Fetching astronomy data for {location_query}")
        astronomy_data = weather_client.get_astronomy(location_query, today)
        
        # Update sunrise/sunset in daily_weather
        if astronomy_data.get('sunrise') and astronomy_data.get('sunset'):
            try:
                sunrise_time = datetime.strptime(astronomy_data['sunrise'], '%I:%M %p').time()
                sunset_time = datetime.strptime(astronomy_data['sunset'], '%I:%M %p').time()
                
                update_query = "UPDATE daily_weather SET sunrise = %s, sunset = %s WHERE location_id = %s AND date = %s"
                Database.execute_query(update_query, (sunrise_time, sunset_time, location_id, today), fetch=False)
            except ValueError:
                logger.warning(f"Could not parse sunrise/sunset times: {astronomy_data.get('sunrise')}, {astronomy_data.get('sunset')}")
        
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
        
        try:
            moonrise_time = None
            moonset_time = None
            if astronomy_data.get('moonrise'):
                moonrise_time = datetime.strptime(astronomy_data['moonrise'], '%I:%M %p').time()
            if astronomy_data.get('moonset'):
                moonset_time = datetime.strptime(astronomy_data['moonset'], '%I:%M %p').time()
            
            Database.execute_query(moon_query, (
                location_id, today,
                moonrise_time,
                moonset_time,
                astronomy_data.get('moon_phase'),
                float(astronomy_data.get('moon_illumination', 0)) if astronomy_data.get('moon_illumination') else None
            ), fetch=False)
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse moon times: {e}")
        
        # Get full forecast data (7 days, skip today as we already have it)
        logger.info(f"Fetching 7-day forecast data for {location_query}")
        forecast_data = weather_client.get_forecast(location_query, days=7)
        
        # Insert forecast data (skip today, start from tomorrow)
        forecast_query = """
            INSERT INTO forecasts 
            (location_id, forecast_date, high_temp, low_temp, precipitation_mm, 
             humidity, wind_speed_kmh, condition_text, condition_icon, chance_of_rain)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                high_temp = VALUES(high_temp),
                low_temp = VALUES(low_temp),
                precipitation_mm = VALUES(precipitation_mm),
                humidity = VALUES(humidity),
                wind_speed_kmh = VALUES(wind_speed_kmh),
                condition_text = VALUES(condition_text),
                condition_icon = VALUES(condition_icon),
                chance_of_rain = VALUES(chance_of_rain)
        """
        
        for forecast in forecast_data.get('forecasts', []):
            try:
                forecast_date = datetime.strptime(forecast['date'], '%Y-%m-%d').date()
                # Skip today's forecast (we already stored it in daily_weather)
                if forecast_date == today:
                    continue
                Database.execute_query(forecast_query, (
                    location_id, forecast_date,
                    forecast.get('high_temp'),
                    forecast.get('low_temp'),
                    forecast.get('precipitation_mm', 0),
                    forecast.get('humidity'),
                    forecast.get('wind_speed_kmh'),
                    forecast.get('condition_text'),
                    forecast.get('condition_icon'),
                    forecast.get('chance_of_rain', 0)
                ), fetch=False)
            except (ValueError, KeyError) as e:
                logger.warning(f"Error inserting forecast: {e}")
        
        # Get tides if US location
        if location.country == 'United States of America' and location.latitude and location.longitude:
            logger.info(f"Fetching tide data for US location {location.name}")
            
            # Find or get NOAA station
            if not location.noaa_station_id:
                station = tides_client.find_nearest_station(location.latitude, location.longitude)
                if station:
                    location.update_noaa_station(station['station_id'])
                    location.noaa_station_id = station['station_id']
            
            if location.noaa_station_id:
                tides = tides_client.get_tides(location.noaa_station_id, today)
                
                # Insert tide data
                tide_query = """
                    INSERT INTO tides (location_id, date, time, tide_type, height_meters)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                for tide in tides:
                    Database.execute_query(tide_query, (
                        location_id, today,
                        tide['time'],
                        tide['tide_type'],
                        tide['height_meters']
                    ), fetch=False)
        
        logger.info(f"Successfully collected weather data for location {location_id}")
        return {'success': True, 'message': 'Data collected', 'collected': True}
        
    except Exception as e:
        logger.error(f"Error collecting weather data: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


@app.route('/')
def index():
    """Main dashboard page."""
    locations = Location.get_all()
    logger.info(f"Found {len(locations)} locations in database")
    
    # Collect data for all locations if needed
    for location in locations:
        collect_daily_weather(location.id)
    
    # Get today's weather for all locations
    today = datetime.now().date()
    locations_data = []
    
    for location in locations:
        query = """
            SELECT dw.*, mp.moon_phase, mp.moon_illumination
            FROM daily_weather dw
            LEFT JOIN moon_phases mp ON dw.location_id = mp.location_id AND dw.date = mp.date
            WHERE dw.location_id = %s AND dw.date = %s
        """
        weather = Database.execute_query(query, (location.id, today))
        logger.info(f"Location {location.id} ({location.name}): Found {len(weather) if weather else 0} weather records")
        
        # Get forecast for this location (next 7 days)
        forecast_query = """
            SELECT * FROM forecasts
            WHERE location_id = %s AND forecast_date > %s
            ORDER BY forecast_date ASC
            LIMIT 7
        """
        forecast = Database.execute_query(forecast_query, (location.id, today))
        logger.info(f"Location {location.id} ({location.name}): Found {len(forecast) if forecast else 0} forecast records")
        
        # Convert Location object to dict for template
        location_dict = {
            'id': location.id,
            'name': location.name,
            'country': location.country,
            'region': location.region,
            'latitude': float(location.latitude) if location.latitude else None,
            'longitude': float(location.longitude) if location.longitude else None,
            'timezone': location.timezone,
            'noaa_station_id': location.noaa_station_id
        }
        
        locations_data.append({
            'location': location_dict,
            'weather': weather[0] if weather else None,
            'forecast': forecast if forecast else []
        })
    
    logger.info(f"Rendering template with {len(locations_data)} locations")
    return render_template('index.html', locations_data=locations_data)


def get_moon_phase_icon(moon_phase: str) -> str:
    """
    Get emoji icon for moon phase.
    
    Args:
        moon_phase: Moon phase text (e.g., "Waxing Crescent", "Full Moon")
        
    Returns:
        Emoji string for the moon phase
    """
    if not moon_phase:
        return ""
    
    moon_phase_lower = moon_phase.lower()
    
    # Map moon phases to emojis
    moon_icons = {
        'new moon': '🌑',
        'waxing crescent': '🌒',
        'first quarter': '🌓',
        'waxing gibbous': '🌔',
        'full moon': '🌕',
        'waning gibbous': '🌖',
        'last quarter': '🌗',
        'waning crescent': '🌘',
        'third quarter': '🌗',  # Alternative name for last quarter
    }
    
    # Try exact match first
    if moon_phase_lower in moon_icons:
        return moon_icons[moon_phase_lower]
    
    # Try partial matches
    if 'new' in moon_phase_lower:
        return '🌑'
    elif 'waxing crescent' in moon_phase_lower:
        return '🌒'
    elif 'first quarter' in moon_phase_lower:
        return '🌓'
    elif 'waxing gibbous' in moon_phase_lower:
        return '🌔'
    elif 'full' in moon_phase_lower:
        return '🌕'
    elif 'waning gibbous' in moon_phase_lower:
        return '🌖'
    elif 'last quarter' in moon_phase_lower or 'third quarter' in moon_phase_lower:
        return '🌗'
    elif 'waning crescent' in moon_phase_lower:
        return '🌘'
    
    # Default fallback
    return '🌙'


@app.route('/location/<int:location_id>')
def location_detail(location_id: int):
    """Location detail page with historical data."""
    location = Location.get_by_id(location_id)
    if not location:
        return "Location not found", 404
    
    # Collect data if needed
    collect_daily_weather(location_id)
    
    today = datetime.now().date()
    
    # Get today's weather
    query = """
        SELECT dw.*, mp.moon_phase, mp.moon_illumination, mp.moonrise, mp.moonset
        FROM daily_weather dw
        LEFT JOIN moon_phases mp ON dw.location_id = mp.location_id AND dw.date = mp.date
        WHERE dw.location_id = %s AND dw.date = %s
    """
    today_weather = Database.execute_query(query, (location_id, today))
    
    # Convert timedelta objects to formatted time strings
    if today_weather:
        weather_dict = today_weather[0]
        # Helper function to convert timedelta to HH:MM string
        def format_timedelta(td):
            if td and isinstance(td, timedelta):
                hours = td.seconds // 3600
                minutes = (td.seconds % 3600) // 60
                return f"{hours:02d}:{minutes:02d}"
            return td
        
        weather_dict['sunrise'] = format_timedelta(weather_dict.get('sunrise'))
        weather_dict['sunset'] = format_timedelta(weather_dict.get('sunset'))
        weather_dict['moonrise'] = format_timedelta(weather_dict.get('moonrise'))
        weather_dict['moonset'] = format_timedelta(weather_dict.get('moonset'))
        # Add moon phase icon
        weather_dict['moon_phase_icon'] = get_moon_phase_icon(weather_dict.get('moon_phase'))
    
    # Get historical data (last 30 days)
    start_date = today - timedelta(days=30)
    hist_query = """
        SELECT dw.*, mp.moon_phase, mp.moon_illumination
        FROM daily_weather dw
        LEFT JOIN moon_phases mp ON dw.location_id = mp.location_id AND dw.date = mp.date
        WHERE dw.location_id = %s AND dw.date >= %s AND dw.date < %s
        ORDER BY dw.date DESC
    """
    historical = Database.execute_query(hist_query, (location_id, start_date, today))
    
    # Add moon phase icons to historical data
    if historical:
        for day in historical:
            day['moon_phase_icon'] = get_moon_phase_icon(day.get('moon_phase'))
    
    # Get forecast
    forecast_query = """
        SELECT * FROM forecasts
        WHERE location_id = %s AND forecast_date > %s
        ORDER BY forecast_date ASC
        LIMIT 7
    """
    forecast = Database.execute_query(forecast_query, (location_id, today))
    
    # Get tides if available
    tides = None
    if location.noaa_station_id:
        tide_query = """
            SELECT * FROM tides
            WHERE location_id = %s AND date = %s
            ORDER BY time ASC
        """
        tides = Database.execute_query(tide_query, (location_id, today))
        # Convert tide time from timedelta to formatted string
        if tides:
            for tide in tides:
                if tide.get('time') and isinstance(tide['time'], timedelta):
                    td = tide['time']
                    hours = td.seconds // 3600
                    minutes = (td.seconds % 3600) // 60
                    tide['time'] = f"{hours:02d}:{minutes:02d}"
    
    # Convert Location object to dict for template
    location_dict = {
        'id': location.id,
        'name': location.name,
        'country': location.country,
        'region': location.region,
        'latitude': float(location.latitude) if location.latitude else None,
        'longitude': float(location.longitude) if location.longitude else None,
        'timezone': location.timezone,
        'noaa_station_id': location.noaa_station_id
    }
    
    return render_template('location.html', 
                         location=location_dict,
                         today_weather=today_weather[0] if today_weather else None,
                         historical=historical,
                         forecast=forecast,
                         tides=tides,
                         get_moon_phase_icon=get_moon_phase_icon)


@app.route('/api/weather/<int:location_id>')
def api_weather(location_id: int):
    """Get current weather for a location (triggers collection if needed)."""
    try:
        result = collect_daily_weather(location_id)
        
        if not result['success']:
            return jsonify(result), 404
        
        location = Location.get_by_id(location_id)
        if not location:
            return jsonify({'success': False, 'error': 'Location not found'}), 404
        
        today = datetime.now().date()
        
        query = """
            SELECT dw.*, mp.moon_phase, mp.moon_illumination
            FROM daily_weather dw
            LEFT JOIN moon_phases mp ON dw.location_id = mp.location_id AND dw.date = mp.date
            WHERE dw.location_id = %s AND dw.date = %s
        """
        weather = Database.execute_query(query, (location_id, today))
        
        if weather:
            return jsonify({'success': True, 'data': weather[0]})
        else:
            return jsonify({'success': False, 'error': 'Weather data not available'}), 404
    except Exception as e:
        logger.error(f"Error in api_weather: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/forecast/<int:location_id>')
def api_forecast(location_id: int):
    """Get forecast for a location."""
    location = Location.get_by_id(location_id)
    if not location:
        return jsonify({'success': False, 'error': 'Location not found'}), 404
    
    today = datetime.now().date()
    query = """
        SELECT * FROM forecasts
        WHERE location_id = %s AND forecast_date > %s
        ORDER BY forecast_date ASC
        LIMIT 7
    """
    forecast = Database.execute_query(query, (location_id, today))
    
    return jsonify({'success': True, 'data': forecast})


@app.route('/api/moon/<int:location_id>')
def api_moon(location_id: int):
    """Get moon phase data for a location."""
    location = Location.get_by_id(location_id)
    if not location:
        return jsonify({'success': False, 'error': 'Location not found'}), 404
    
    date_str = request.args.get('date')
    if date_str:
        try:
            query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
    else:
        query_date = datetime.now().date()
    
    query = "SELECT * FROM moon_phases WHERE location_id = %s AND date = %s"
    moon_data = Database.execute_query(query, (location_id, query_date))
    
    if moon_data:
        return jsonify({'success': True, 'data': moon_data[0]})
    else:
        return jsonify({'success': False, 'error': 'Moon phase data not available'}), 404


@app.route('/api/tides/<int:location_id>')
def api_tides(location_id: int):
    """Get tide data for a location (US only)."""
    location = Location.get_by_id(location_id)
    if not location:
        return jsonify({'success': False, 'error': 'Location not found'}), 404
    
    if location.country != 'United States of America':
        return jsonify({'success': False, 'error': 'Tides only available for US locations'}), 400
    
    date_str = request.args.get('date')
    if date_str:
        try:
            query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
    else:
        query_date = datetime.now().date()
    
    query = """
        SELECT * FROM tides
        WHERE location_id = %s AND date = %s
        ORDER BY time ASC
    """
    tides = Database.execute_query(query, (location_id, query_date))
    
    return jsonify({'success': True, 'data': tides})


@app.route('/api/locations', methods=['GET'])
def api_locations():
    """Get all locations."""
    locations = Location.get_all()
    return jsonify({
        'success': True,
        'data': [{
            'id': loc.id,
            'name': loc.name,
            'country': loc.country,
            'region': loc.region,
            'latitude': float(loc.latitude) if loc.latitude else None,
            'longitude': float(loc.longitude) if loc.longitude else None,
            'timezone': loc.timezone,
            'noaa_station_id': loc.noaa_station_id
        } for loc in locations]
    })


@app.route('/api/locations', methods=['POST'])
def api_add_location():
    """Add a new location."""
    data = request.json
    
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'error': 'Location name is required'}), 400
    
    # Try to get location details from WeatherAPI
    try:
        weather_data = weather_client.get_current_weather(name)
        loc_data = weather_data['location']
        
        location = Location.create(
            name=loc_data.get('name') or name,
            country=loc_data.get('country'),
            region=loc_data.get('region'),
            latitude=loc_data.get('latitude'),
            longitude=loc_data.get('longitude'),
            timezone=loc_data.get('timezone')
        )
        
        # Collect initial data
        collect_daily_weather(location.id)
        
        return jsonify({
            'success': True,
            'data': {
                'id': location.id,
                'name': location.name,
                'country': location.country,
                'region': location.region
            }
        })
    except Exception as e:
        logger.error(f"Error adding location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search')
def api_search():
    """Search for locations via WeatherAPI."""
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify({'success': False, 'error': 'Query must be at least 2 characters'}), 400
    
    try:
        locations = weather_client.search_locations(query)
        return jsonify({'success': True, 'data': locations})
    except Exception as e:
        logger.error(f"Location search error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/weekly-average/<int:location_id>')
def api_weekly_average(location_id: int):
    """Get average high and low temperatures for the previous week (6 days prior + today = 7 days)."""
    location = Location.get_by_id(location_id)
    if not location:
        return jsonify({'success': False, 'error': 'Location not found'}), 404
    
    today = datetime.now().date()
    # 6 days prior + today = 7 days total
    start_date = today - timedelta(days=6)
    
    query = """
        SELECT 
            AVG(high_temp) as avg_high,
            AVG(low_temp) as avg_low,
            COUNT(*) as days_count,
            MIN(date) as start_date,
            MAX(date) as end_date
        FROM daily_weather
        WHERE location_id = %s AND date >= %s AND date <= %s
    """
    
    result = Database.execute_query(query, (location_id, start_date, today))
    
    if result and result[0]['days_count'] and result[0]['days_count'] > 0:
        return jsonify({
            'success': True,
            'data': {
                'avg_high': float(result[0]['avg_high']) if result[0]['avg_high'] else None,
                'avg_low': float(result[0]['avg_low']) if result[0]['avg_low'] else None,
                'days_count': result[0]['days_count'],
                'start_date': result[0]['start_date'].strftime('%Y-%m-%d') if result[0]['start_date'] else None,
                'end_date': result[0]['end_date'].strftime('%Y-%m-%d') if result[0]['end_date'] else None,
                'period': 'Last 7 days (6 days prior + today)'
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Insufficient data for weekly average'
        }), 404


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'weather-monitoring',
        'port': config.PORT
    })


if __name__ == '__main__':
    logger.info(f"Starting Weather Monitoring App on port {config.PORT}...")
    logger.info(f"URL: http://localhost:{config.PORT}")
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)
