"""
Weather data service for fetching and parsing METAR/TAF data
"""
import requests
import logging
from typing import List, Optional
from datetime import datetime
from models import WeatherCondition, Waypoint

logger = logging.getLogger(__name__)


class WeatherService:
    """Service for fetching and processing weather data"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize weather service
        
        Args:
            api_key: Optional API key for weather service (e.g., OpenWeather)
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    def fetch_weather_for_waypoint(self, waypoint: Waypoint) -> Optional[WeatherCondition]:
        """
        Fetch current weather for a waypoint
        
        Args:
            waypoint: Flight waypoint
            
        Returns:
            WeatherCondition object or None if fetch fails
        """
        try:
            # In production, use real API. For demo, generate realistic data
            return self._generate_mock_weather(waypoint)
        except Exception as e:
            logger.error(f"Error fetching weather for {waypoint.name}: {e}")
            return None
    
    def fetch_weather_for_route(self, waypoints: List[Waypoint]) -> List[WeatherCondition]:
        """
        Fetch weather for all waypoints on a route
        
        Args:
            waypoints: List of waypoints
            
        Returns:
            List of weather conditions
        """
        weather_data = []
        for waypoint in waypoints:
            weather = self.fetch_weather_for_waypoint(waypoint)
            if weather:
                weather_data.append(weather)
        return weather_data
    
    def _generate_mock_weather(self, waypoint: Waypoint) -> WeatherCondition:
        """
        Generate realistic mock weather data for demonstration
        
        Args:
            waypoint: Flight waypoint
            
        Returns:
            Mock weather condition
        """
        import random
        
        # Simulate realistic weather variations
        base_temp = 15 - (waypoint.latitude / 10)  # Colder at higher latitudes
        
        wind_directions = [270, 280, 290, 300]  # Westerly winds (jet stream)
        wind_speeds = [50, 75, 100, 125, 150]  # Knots
        
        conditions_list = ["Clear", "Few Clouds", "Scattered Clouds", "Broken Clouds", "Light Turbulence"]
        
        return WeatherCondition(
            location=waypoint.name,
            timestamp=datetime.utcnow(),
            temperature=round(base_temp + random.uniform(-10, 10), 1),
            wind_speed=random.choice(wind_speeds),
            wind_direction=random.choice(wind_directions),
            visibility=10.0,
            conditions=random.choice(conditions_list),
            metar_raw=f"METAR {waypoint.name} AUTO {datetime.utcnow().strftime('%d%H%MZ')}"
        )
    
    def analyze_wind_component(self, weather: WeatherCondition, course: int) -> Dict[str, float]:
        """
        Analyze headwind/tailwind component
        
        Args:
            weather: Weather condition
            course: Aircraft course (degrees)
            
        Returns:
            Dict with headwind/tailwind and crosswind components
        """
        import math
        
        # Calculate angle difference
        angle_diff = abs(weather.wind_direction - course)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        # Calculate components
        headwind_component = weather.wind_speed * math.cos(math.radians(angle_diff))
        crosswind_component = weather.wind_speed * math.sin(math.radians(angle_diff))
        
        return {
            "headwind": headwind_component if headwind_component > 0 else 0,
            "tailwind": abs(headwind_component) if headwind_component < 0 else 0,
            "crosswind": crosswind_component
        }
    
    def get_jet_stream_info(self, waypoints: List[Waypoint], altitude: int) -> Dict:
        """
        Analyze jet stream effects on route
        
        Args:
            waypoints: Route waypoints
            altitude: Cruise altitude
            
        Returns:
            Jet stream analysis
        """
        # Simplified: jet stream typically at 30000-40000 ft, westerly
        if 30000 <= altitude <= 42000:
            avg_latitude = sum(w.latitude for w in waypoints) / len(waypoints)
            
            # Jet stream strongest at 30-60 degrees latitude
            if 30 <= abs(avg_latitude) <= 60:
                return {
                    "present": True,
                    "strength": "strong",
                    "direction": "westerly",
                    "benefit": "Favorable for westbound flights at this altitude"
                }
        
        return {
            "present": False,
            "strength": "none",
            "direction": None,
            "benefit": None
        }
