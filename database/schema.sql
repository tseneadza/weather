-- Weather Monitoring App Database Schema
-- Creates the weather schema and all required tables

CREATE SCHEMA IF NOT EXISTS weather;
USE weather;

-- Locations table: Stores all monitored locations
CREATE TABLE IF NOT EXISTS locations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    region VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    timezone VARCHAR(50),
    noaa_station_id VARCHAR(50) NULL COMMENT 'NOAA tide station ID for US locations',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_location (name, country, region),
    INDEX idx_country (country),
    INDEX idx_coordinates (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Daily weather table: Stores collected daily weather data
CREATE TABLE IF NOT EXISTS daily_weather (
    id INT PRIMARY KEY AUTO_INCREMENT,
    location_id INT NOT NULL,
    date DATE NOT NULL,
    high_temp DECIMAL(5, 2) COMMENT 'High temperature in Celsius',
    low_temp DECIMAL(5, 2) COMMENT 'Low temperature in Celsius',
    avg_temp DECIMAL(5, 2) COMMENT 'Average temperature in Celsius',
    precipitation_mm DECIMAL(6, 2) DEFAULT 0 COMMENT 'Precipitation in millimeters',
    humidity INT COMMENT 'Humidity percentage',
    wind_speed_kmh DECIMAL(5, 2) COMMENT 'Wind speed in km/h',
    wind_direction VARCHAR(10) COMMENT 'Wind direction (N, NE, E, etc.)',
    pressure_mb DECIMAL(7, 2) COMMENT 'Atmospheric pressure in millibars',
    visibility_km DECIMAL(5, 2) COMMENT 'Visibility in kilometers',
    uv_index DECIMAL(3, 1) COMMENT 'UV index',
    condition_text VARCHAR(100) COMMENT 'Weather condition description',
    condition_icon VARCHAR(255) COMMENT 'Weather condition icon URL',
    sunrise TIME COMMENT 'Sunrise time',
    sunset TIME COMMENT 'Sunset time',
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_daily (location_id, date),
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    INDEX idx_date (date),
    INDEX idx_location_date (location_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Moon phases table: Stores moon phase and astronomy data
CREATE TABLE IF NOT EXISTS moon_phases (
    id INT PRIMARY KEY AUTO_INCREMENT,
    location_id INT NOT NULL,
    date DATE NOT NULL,
    moonrise TIME COMMENT 'Moonrise time',
    moonset TIME COMMENT 'Moonset time',
    moon_phase VARCHAR(50) COMMENT 'Moon phase name (New Moon, Waxing Crescent, etc.)',
    moon_illumination DECIMAL(5, 2) COMMENT 'Moon illumination percentage (0-100)',
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_moon (location_id, date),
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    INDEX idx_date (date),
    INDEX idx_location_date (location_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Forecasts table: Stores weather forecast data
CREATE TABLE IF NOT EXISTS forecasts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    location_id INT NOT NULL,
    forecast_date DATE NOT NULL,
    high_temp DECIMAL(5, 2) COMMENT 'High temperature in Celsius',
    low_temp DECIMAL(5, 2) COMMENT 'Low temperature in Celsius',
    precipitation_mm DECIMAL(6, 2) DEFAULT 0 COMMENT 'Precipitation in millimeters',
    humidity INT COMMENT 'Humidity percentage',
    wind_speed_kmh DECIMAL(5, 2) COMMENT 'Wind speed in km/h',
    condition_text VARCHAR(100) COMMENT 'Weather condition description',
    condition_icon VARCHAR(255) COMMENT 'Weather condition icon URL',
    chance_of_rain INT COMMENT 'Chance of rain percentage',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_forecast (location_id, forecast_date),
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    INDEX idx_forecast_date (forecast_date),
    INDEX idx_location_date (location_id, forecast_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tides table: Stores tide predictions (US locations only)
CREATE TABLE IF NOT EXISTS tides (
    id INT PRIMARY KEY AUTO_INCREMENT,
    location_id INT NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    tide_type ENUM('high', 'low') NOT NULL,
    height_meters DECIMAL(5, 3) COMMENT 'Tide height in meters',
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_location_date (location_id, date),
    INDEX idx_date_time (date, time),
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
