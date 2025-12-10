"""
Database connection and models for Weather Monitoring Application
"""

import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, date
from decimal import Decimal
import logging
import config

logger = logging.getLogger(__name__)

class Database:
    """Database connection manager with connection pooling."""
    
    _pool = None
    
    @classmethod
    def get_connection(cls):
        """Get a database connection from the pool."""
        if cls._pool is None:
            try:
                cls._pool = pooling.MySQLConnectionPool(
                    pool_name="weather_pool",
                    pool_size=5,
                    pool_reset_session=True,
                    **config.DB_CONFIG
                )
            except Error as e:
                print(f"Error creating connection pool: {e}")
                raise
        
        return cls._pool.get_connection()
    
    @classmethod
    def execute_query(cls, query: str, params: Tuple = None, fetch: bool = True) -> Optional[List[Dict]]:
        """Execute a query and return results."""
        conn = None
        try:
            conn = cls.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                conn.commit()
                return result
            else:
                conn.commit()
                return None
        except Error as e:
            if conn:
                conn.rollback()
            print(f"Database error: {e}")
            raise
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    @classmethod
    def execute_many(cls, query: str, params_list: List[Tuple]) -> None:
        """Execute a query multiple times with different parameters."""
        conn = None
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
        except Error as e:
            if conn:
                conn.rollback()
            print(f"Database error: {e}")
            raise
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()


class Location:
    """Model for weather locations."""
    
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.name = data.get('name')
        self.country = data.get('country')
        self.region = data.get('region')
        self.latitude = data.get('latitude')
        self.longitude = data.get('longitude')
        self.timezone = data.get('timezone')
        self.noaa_station_id = data.get('noaa_station_id')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
    
    @staticmethod
    def get_by_id(location_id: int) -> Optional['Location']:
        """Get location by ID."""
        query = "SELECT * FROM locations WHERE id = %s"
        results = Database.execute_query(query, (location_id,))
        if results:
            return Location(results[0])
        return None
    
    @staticmethod
    def get_all() -> List['Location']:
        """Get all locations."""
        query = "SELECT * FROM locations ORDER BY name"
        results = Database.execute_query(query)
        return [Location(r) for r in results] if results else []
    
    @staticmethod
    def create(name: str, country: str = None, region: str = None, 
               latitude: float = None, longitude: float = None, 
               timezone: str = None) -> Optional['Location']:
        """Create a new location."""
        query = """
            INSERT INTO locations (name, country, region, latitude, longitude, timezone)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (name, country, region, latitude, longitude, timezone)
        conn = Database.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            location_id = cursor.lastrowid
            return Location.get_by_id(location_id)
        except Error as e:
            conn.rollback()
            logger.error(f"Error creating location: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def update_noaa_station(self, station_id: str):
        """Update NOAA station ID for this location."""
        query = "UPDATE locations SET noaa_station_id = %s WHERE id = %s"
        Database.execute_query(query, (station_id, self.id), fetch=False)


def check_daily_weather_collected(location_id: int, date: date = None) -> bool:
    """Check if daily weather data has been collected for a location and date."""
    if date is None:
        date = datetime.now().date()
    query = "SELECT COUNT(*) as count FROM daily_weather WHERE location_id = %s AND date = %s"
    results = Database.execute_query(query, (location_id, date))
    return results[0]['count'] > 0 if results else False
