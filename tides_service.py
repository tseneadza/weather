"""
NOAA Tides API service for tide predictions (US locations only)
"""

import requests
from typing import Dict, List, Optional
from datetime import datetime, date
import logging
import config

logger = logging.getLogger(__name__)

class NOAATidesClient:
    """Client for NOAA Tides and Currents API."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.NOAA_API_BASE
    
    def find_nearest_station(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Find the nearest NOAA tide station to given coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dictionary with station information or None
        """
        # NOAA API endpoint for finding stations
        url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
        params = {
            'type': 'tidepredictions',
            'units': 'metric'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            stations = response.json().get('stations', [])
            
            if not stations:
                return None
            
            # Find nearest station by calculating distance
            nearest = None
            min_distance = float('inf')
            
            for station in stations:
                try:
                    station_lat = float(station.get('lat', 0))
                    station_lon = float(station.get('lng', 0))
                    
                    # Simple distance calculation (Haversine would be better but this works)
                    distance = ((latitude - station_lat) ** 2 + (longitude - station_lon) ** 2) ** 0.5
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest = {
                            'station_id': station.get('id'),
                            'name': station.get('name'),
                            'latitude': station_lat,
                            'longitude': station_lon,
                            'distance': distance
                        }
                except (ValueError, TypeError):
                    continue
            
            return nearest if nearest and min_distance < 1.0 else None  # Within ~1 degree
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NOAA station search failed: {e}")
            return None
    
    def get_tides(self, station_id: str, date: date = None) -> List[Dict]:
        """
        Get tide predictions for a station and date.
        
        Args:
            station_id: NOAA station ID
            date: Date for tide predictions (default: today)
            
        Returns:
            List of tide predictions (high/low tides)
        """
        if date is None:
            date = datetime.now().date()
        
        params = {
            'product': 'predictions',
            'application': 'NOS.COOPS.TAC.WL',
            'datum': 'MLLW',
            'station': station_id,
            'begin_date': date.strftime('%Y%m%d'),
            'end_date': date.strftime('%Y%m%d'),
            'time_zone': 'gmt',
            'units': 'metric',
            'interval': 'h',
            'format': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            predictions = data.get('predictions', [])
            tides = []
            
            for pred in predictions:
                try:
                    time_str = pred.get('t')
                    height = float(pred.get('v', 0))
                    
                    # Parse time
                    time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                    
                    # Determine if high or low tide (simplified: compare with average)
                    # In practice, you'd compare with surrounding values
                    tide_type = 'high' if height > 0 else 'low'
                    
                    tides.append({
                        'time': time_obj.time(),
                        'tide_type': tide_type,
                        'height_meters': height
                    })
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Error parsing tide prediction: {e}")
                    continue
            
            # Sort by time and determine high/low more accurately
            tides.sort(key=lambda x: x['time'])
            if len(tides) > 1:
                # Simple heuristic: if height increases, it's rising (low to high)
                # If decreases, it's falling (high to low)
                for i in range(1, len(tides)):
                    if tides[i]['height_meters'] > tides[i-1]['height_meters']:
                        tides[i-1]['tide_type'] = 'low'
                        tides[i]['tide_type'] = 'high'
                    else:
                        tides[i-1]['tide_type'] = 'high'
                        tides[i]['tide_type'] = 'low'
            
            return tides
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NOAA tides request failed: {e}")
            return []
    
    def get_tide_predictions(self, station_id: str, start_date: date, end_date: date) -> List[Dict]:
        """
        Get tide predictions for a date range.
        
        Args:
            station_id: NOAA station ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of tide predictions grouped by date
        """
        params = {
            'product': 'predictions',
            'application': 'NOS.COOPS.TAC.WL',
            'datum': 'MLLW',
            'station': station_id,
            'begin_date': start_date.strftime('%Y%m%d'),
            'end_date': end_date.strftime('%Y%m%d'),
            'time_zone': 'gmt',
            'units': 'metric',
            'interval': 'h',
            'format': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            predictions = data.get('predictions', [])
            tides_by_date = {}
            
            for pred in predictions:
                try:
                    time_str = pred.get('t')
                    height = float(pred.get('v', 0))
                    
                    time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                    date_key = time_obj.date()
                    
                    if date_key not in tides_by_date:
                        tides_by_date[date_key] = []
                    
                    tides_by_date[date_key].append({
                        'time': time_obj.time(),
                        'height_meters': height
                    })
                except (ValueError, TypeError, KeyError):
                    continue
            
            # Determine high/low for each date
            result = []
            for date_key, tides in tides_by_date.items():
                tides.sort(key=lambda x: x['time'])
                if len(tides) > 1:
                    for i in range(1, len(tides)):
                        if tides[i]['height_meters'] > tides[i-1]['height_meters']:
                            tides[i-1]['tide_type'] = 'low'
                            tides[i]['tide_type'] = 'high'
                        else:
                            tides[i-1]['tide_type'] = 'high'
                            tides[i]['tide_type'] = 'low'
                
                result.append({
                    'date': date_key,
                    'tides': tides
                })
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NOAA tides range request failed: {e}")
            return []
