# Weather Monitoring App

A Flask web application for monitoring weather conditions, collecting daily weather data automatically, storing historical records in MySQL, and providing forecasts. Includes moon phase tracking and tide predictions for US locations.

## Features

- **Daily Weather Monitoring**: Automatically collects weather data when the app is accessed
- **Multiple Locations**: Add and monitor weather for multiple cities
- **Historical Data**: View weather history for the last 30 days
- **7-Day Forecast**: Weather predictions for the upcoming week
- **Moon Phases**: Track moon phases and illumination for all locations
- **Tide Predictions**: Tide data for US coastal locations (via NOAA API)
- **Automatic Data Collection**: Data is collected daily automatically when you access the app

## Requirements

- Python 3.8+
- MySQL 5.7+ or MySQL 8.0+
- WeatherAPI.com API key (free tier: 1M calls/month)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your settings:
- `DB_PASSWORD`: Your MySQL password
- `WEATHER_API_KEY`: Your WeatherAPI.com API key (get one at https://www.weatherapi.com/signup.aspx)

### 3. Set Up Database

Create the MySQL database schema:

```bash
mysql -u root -p < database/schema.sql
```

Or manually:
```sql
mysql -u root -p
source database/schema.sql
```

### 4. Run the Application

Using the `go` script:
```bash
go weather
```

Or directly:
```bash
python3 app.py
```

The app will be available at `http://localhost:5105`

## Usage

### Adding Locations

1. Click "Add Location" on the dashboard
2. Search for a city name
3. Select a location from the results
4. The app will automatically collect weather data for that location

### Viewing Weather Data

- **Dashboard**: See all locations and today's weather at a glance
- **Location Detail**: Click "View Details" to see:
  - Current conditions
  - Historical data (last 30 days)
  - 7-day forecast
  - Moon phase information
  - Tide predictions (US locations only)

## API Endpoints

- `GET /` - Main dashboard
- `GET /location/<id>` - Location detail page
- `GET /api/weather/<location_id>` - Get current weather (triggers collection)
- `GET /api/forecast/<location_id>` - Get forecast
- `GET /api/moon/<location_id>?date=YYYY-MM-DD` - Get moon phase data
- `GET /api/tides/<location_id>?date=YYYY-MM-DD` - Get tide data (US only)
- `GET /api/locations` - List all locations
- `POST /api/locations` - Add new location
- `GET /api/search?q=<query>` - Search for locations
- `GET /api/health` - Health check

## Data Collection

The app automatically collects weather data when:
- You access the dashboard or a location page
- Data hasn't been collected for that location today

This ensures you always have up-to-date information without manual intervention.

## Database Schema

The app uses a MySQL schema called `weather` with the following tables:

- `locations` - Monitored locations
- `daily_weather` - Daily weather records
- `moon_phases` - Moon phase data
- `forecasts` - Weather forecast data
- `tides` - Tide predictions (US locations)

## Weather API

This app uses [WeatherAPI.com](https://www.weatherapi.com/) for weather data:
- Free tier: 1 million API calls per month
- Provides current weather, forecasts, and astronomy data
- Global coverage

## Tides API

For US locations, the app uses the [NOAA Tides and Currents API](https://tidesandcurrents.noaa.gov/api/):
- Free, no API key required
- US locations only
- Provides high/low tide predictions

## Project Structure

```
Weather/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── weather_service.py     # WeatherAPI.com client
├── tides_service.py       # NOAA Tides API client
├── database/
│   ├── db.py             # Database connection and models
│   └── schema.sql        # Database schema
├── templates/            # HTML templates
├── static/               # CSS and JavaScript
└── requirements.txt      # Python dependencies
```

## Troubleshooting

### Database Connection Issues

- Verify MySQL is running: `brew services list` (macOS) or `systemctl status mysql` (Linux)
- Check database credentials in `.env`
- Ensure the `weather` schema exists: `SHOW DATABASES;`

### API Errors

- Verify your WeatherAPI.com API key is correct
- Check API rate limits (free tier: 1M calls/month)
- Ensure you have internet connectivity

### No Tide Data

- Tides are only available for US locations
- The app automatically finds the nearest NOAA station
- Some inland locations may not have tide stations nearby

## License

This project is part of the Codehome workspace.
