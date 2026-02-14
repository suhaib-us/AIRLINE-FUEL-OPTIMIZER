"""
Unit tests for Airline Fuel Optimization Agent
"""
import pytest
from datetime import datetime
import sys
sys.path.insert(0, '../src')

from models import FlightPlan, Waypoint, AircraftPerformance
from weather_service import WeatherService
from optimization_engine import FuelOptimizationEngine


class TestModels:
    """Test data models"""
    
    def test_waypoint_creation(self):
        """Test waypoint model"""
        wp = Waypoint(name="JFK", latitude=40.6413, longitude=-73.7781)
        assert wp.name == "JFK"
        assert -90 <= wp.latitude <= 90
        assert -180 <= wp.longitude <= 180
    
    def test_flight_plan_creation(self):
        """Test flight plan model"""
        waypoints = [
            Waypoint(name="JFK", latitude=40.64, longitude=-73.78),
            Waypoint(name="LAX", latitude=33.94, longitude=-118.41)
        ]
        
        fp = FlightPlan(
            flight_id="TEST001",
            origin="JFK",
            destination="LAX",
            aircraft_type="B737-800",
            departure_time=datetime.utcnow(),
            route_waypoints=waypoints,
            planned_fuel=15000,
            cruise_altitude=36000
        )
        
        assert fp.flight_id == "TEST001"
        assert len(fp.route_waypoints) == 2
        assert fp.cruise_altitude == 36000


class TestWeatherService:
    """Test weather service"""
    
    def test_weather_fetch(self):
        """Test weather fetching"""
        service = WeatherService()
        wp = Waypoint(name="TEST", latitude=40.0, longitude=-75.0)
        
        weather = service.fetch_weather_for_waypoint(wp)
        
        assert weather is not None
        assert weather.location == "TEST"
        assert weather.wind_speed > 0
    
    def test_wind_component_analysis(self):
        """Test wind component calculation"""
        service = WeatherService()
        wp = Waypoint(name="TEST", latitude=40.0, longitude=-75.0)
        weather = service.fetch_weather_for_waypoint(wp)
        
        components = service.analyze_wind_component(weather, 270)
        
        assert "headwind" in components
        assert "tailwind" in components
        assert "crosswind" in components


class TestOptimizationEngine:
    """Test optimization engine"""
    
    def test_distance_calculation(self):
        """Test great circle distance"""
        service = WeatherService()
        engine = FuelOptimizationEngine(service)
        
        jfk = Waypoint(name="JFK", latitude=40.6413, longitude=-73.7781)
        lax = Waypoint(name="LAX", latitude=33.9416, longitude=-118.4085)
        
        distance = engine.calculate_distance(jfk, lax)
        
        # JFK to LAX is approximately 2,150 nautical miles
        assert 2100 < distance < 2200
    
    def test_fuel_optimization(self):
        """Test fuel optimization"""
        service = WeatherService()
        engine = FuelOptimizationEngine(service)
        
        waypoints = [
            Waypoint(name="JFK", latitude=40.64, longitude=-73.78),
            Waypoint(name="LAX", latitude=33.94, longitude=-118.41)
        ]
        
        fp = FlightPlan(
            flight_id="TEST001",
            origin="JFK",
            destination="LAX",
            aircraft_type="B737-800",
            departure_time=datetime.utcnow(),
            route_waypoints=waypoints,
            planned_fuel=15000,
            cruise_altitude=36000,
            passenger_count=150,
            cargo_weight=5000
        )
        
        result = engine.optimize_flight(fp)
        
        assert result is not None
        assert result.flight_id == "TEST001"
        assert result.fuel_savings >= 0
        assert 0 <= result.confidence_score <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
