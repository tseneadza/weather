"""
WeatherAPI.com service wrapper for weather data
"""

import requests
from typing import Dict, List, Optional
from datetime import datetime, date
import logging
import config

logger = logging.getLogger(__name__)

class WeatherAPIClient:
    """Client for WeatherAPI.com API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.WEATHER_API_KEY
        self.base_url = config.WEATHER_API_BASE
        if not self.api_key:
            raise ValueError("WeatherAPI.com API key is required")
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make a request to the WeatherAPI.com API."""
        url = f"{self.base_url}/{endpoint}"
        params['key'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"WeatherAPI request failed: {e}")
            raise
    
    def get_current_weather(self, location: str) -> Dict:
        """
        Get current weather conditions for a location.
        
        Args:
            location: City name, zip code, or lat,lon coordinates
            
        Returns:
            Dictionary with current weather data
        """
        params = {'q': location, 'aqi': 'no'}
        data = self._make_request('current.json', params)
        
        # Normalize the response
        current = data.get('current', {})
        location_data = data.get('location', {})
        
        return {
            'location': {
                'name': location_data.get('name'),
                'country': location_data.get('country'),
                'region': location_data.get('region'),
                'latitude': location_data.get('lat'),
                'longitude': location_data.get('lon'),
                'timezone': location_data.get('tz_id')
            },
            'current': {
                'temp_c': current.get('temp_c'),
                'temp_f': current.get('temp_f'),
                'condition': current.get('condition', {}).get('text'),
                'condition_icon': current.get('condition', {}).get('icon'),
                'humidity': current.get('humidity'),
                'wind_kph': current.get('wind_kph'),
                'wind_dir': current.get('wind_dir'),
                'pressure_mb': current.get('pressure_mb'),
                'precip_mm': current.get('precip_mm', 0),
                'visibility_km': current.get('vis_km'),
                'uv': current.get('uv'),
                'last_updated': current.get('last_updated')
            }
        }
    
    def get_forecast(self, location: str, days: int = 7) -> Dict:
        """
        Get weather forecast for a location.
        
        Args:
            location: City name, zip code, or lat,lon coordinates
            days: Number of forecast days (1-14)
            
        Returns:
            Dictionary with forecast data
        """
        params = {'q': location, 'days': min(days, 14), 'aqi': 'no', 'alerts': 'no'}
        data = self._make_request('forecast.json', params)
        
        location_data = data.get('location', {})
        forecast_days = data.get('forecast', {}).get('forecastday', [])
        
        forecasts = []
        for day in forecast_days:
            day_data = day.get('day', {})
            forecasts.append({
                'date': day.get('date'),
                'high_temp': day_data.get('maxtemp_c'),
                'low_temp': day_data.get('mintemp_c'),
                'precipitation_mm': day_data.get('totalprecip_mm', 0),
                'humidity': day_data.get('avghumidity'),
                'wind_speed_kmh': day_data.get('maxwind_kph'),
                'condition_text': day_data.get('condition', {}).get('text'),
                'condition_icon': day_data.get('condition', {}).get('icon'),
                'chance_of_rain': day_data.get('daily_chance_of_rain', 0)
            })
        
        return {
            'location': {
                'name': location_data.get('name'),
                'country': location_data.get('country'),
                'region': location_data.get('region'),
                'latitude': location_data.get('lat'),
                'longitude': location_data.get('lon'),
                'timezone': location_data.get('tz_id')
            },
            'forecasts': forecasts
        }
    
    def get_astronomy(self, location: str, date: date = None) -> Dict:
        """
        Get astronomy data (moon phases, sunrise/sunset) for a location.
        
        Args:
            location: City name, zip code, or lat,lon coordinates
            date: Date for astronomy data (default: today)
            
        Returns:
            Dictionary with astronomy data
        """
        if date is None:
            date = datetime.now().date()
        
        params = {'q': location, 'dt': date.strftime('%Y-%m-%d')}
        data = self._make_request('astronomy.json', params)
        
        location_data = data.get('location', {})
        astronomy = data.get('astronomy', {}).get('astro', {})
        
        return {
            'location': {
                'name': location_data.get('name'),
                'country': location_data.get('country'),
                'region': location_data.get('region'),
                'latitude': location_data.get('lat'),
                'longitude': location_data.get('lon')
            },
            'date': date.strftime('%Y-%m-%d'),
            'sunrise': astronomy.get('sunrise'),
            'sunset': astronomy.get('sunset'),
            'moonrise': astronomy.get('moonrise'),
            'moonset': astronomy.get('moonset'),
            'moon_phase': astronomy.get('moon_phase'),
            'moon_illumination': astronomy.get('moon_illumination')
        }
    
    def get_historical_weather(self, location: str, date: date) -> Dict:
        """
        Get historical weather data for a specific date.
        
        Args:
            location: City name, zip code, or lat,lon coordinates
            date: Date to get historical data for (up to 7 days in the past for free tier)
            
        Returns:
            Dictionary with historical weather data
        """
        params = {
            'q': location,
            'dt': date.strftime('%Y-%m-%d'),
            'aqi': 'no'
        }
        data = self._make_request('history.json', params)
        
        location_data = data.get('location', {})
        forecast_day = data.get('forecast', {}).get('forecastday', [])
        
        # Get the day's data
        day_data = forecast_day[0].get('day', {}) if forecast_day else {}
        astro_data = forecast_day[0].get('astro', {}) if forecast_day else {}
        
        return {
            'location': {
                'name': location_data.get('name'),
                'country': location_data.get('country'),
                'region': location_data.get('region'),
                'latitude': location_data.get('lat'),
                'longitude': location_data.get('lon'),
                'timezone': location_data.get('tz_id')
            },
            'date': date.strftime('%Y-%m-%d'),
            'high_temp': day_data.get('maxtemp_c'),
            'low_temp': day_data.get('mintemp_c'),
            'avg_temp': day_data.get('avgtemp_c'),
            'precipitation_mm': day_data.get('totalprecip_mm', 0),
            'humidity': day_data.get('avghumidity'),
            'wind_speed_kmh': day_data.get('maxwind_kph'),
            'condition_text': day_data.get('condition', {}).get('text'),
            'condition_icon': day_data.get('condition', {}).get('icon'),
            'sunrise': astro_data.get('sunrise'),
            'sunset': astro_data.get('sunset'),
            'moonrise': astro_data.get('moonrise'),
            'moonset': astro_data.get('moonset'),
            'moon_phase': astro_data.get('moon_phase'),
            'moon_illumination': astro_data.get('moon_illumination')
        }
    
    def search_locations(self, query: str) -> List[Dict]:
        """
        Search for locations.
        
        Args:
            query: Search query (city name, etc.)
            
        Returns:
            List of location dictionaries
        """
        params = {'q': query}
        try:
            data = self._make_request('search.json', params)
            locations = []
            for loc in data:
                locations.append({
                    'name': loc.get('name'),
                    'country': loc.get('country'),
                    'region': loc.get('region'),
                    'latitude': loc.get('lat'),
                    'longitude': loc.get('lon'),
                    'timezone': loc.get('tz_id')
                })
            return locations
        except Exception as e:
            logger.error(f"Location search failed: {e}")
            return []
