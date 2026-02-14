"""
Fuel optimization engine - core logic for route and altitude optimization
"""
import logging
import math
from typing import List, Dict, Tuple
from models import (
    FlightPlan, Waypoint, WeatherCondition, OptimizationResult,
    AircraftPerformance, RecommendationType
)
from weather_service import WeatherService

logger = logging.getLogger(__name__)


class FuelOptimizationEngine:
    """Engine for calculating optimal routes and fuel consumption"""
    
    # Fuel price in USD per kg (approximate)
    FUEL_PRICE_PER_KG = 0.85
    
    # Aircraft performance database
    AIRCRAFT_DB = {
        "B737-800": AircraftPerformance(
            aircraft_type="B737-800",
            max_cruise_altitude=41000,
            optimal_cruise_altitude=36000,
            cruise_speed=450,
            fuel_capacity=26000,
            fuel_burn_rate_base=2400,
            weight_empty=42000,
            max_payload=20000
        ),
        "A320": AircraftPerformance(
            aircraft_type="A320",
            max_cruise_altitude=39000,
            optimal_cruise_altitude=35000,
            cruise_speed=447,
            fuel_capacity=24000,
            fuel_burn_rate_base=2300,
            weight_empty=42400,
            max_payload=19000
        ),
        "B777-300": AircraftPerformance(
            aircraft_type="B777-300",
            max_cruise_altitude=43100,
            optimal_cruise_altitude=38000,
            cruise_speed=490,
            fuel_capacity=181000,
            fuel_burn_rate_base=7500,
            weight_empty=167800,
            max_payload=70000
        )
    }
    
    def __init__(self, weather_service: WeatherService):
        """
        Initialize optimization engine
        
        Args:
            weather_service: Weather data service
        """
        self.weather_service = weather_service
    
    def calculate_distance(self, point1: Waypoint, point2: Waypoint) -> float:
        """
        Calculate great circle distance between two waypoints
        
        Args:
            point1: First waypoint
            point2: Second waypoint
            
        Returns:
            Distance in nautical miles
        """
        # Haversine formula
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in nautical miles
        r = 3440.065
        
        return c * r
    
    def calculate_route_distance(self, waypoints: List[Waypoint]) -> float:
        """
        Calculate total route distance
        
        Args:
            waypoints: List of route waypoints
            
        Returns:
            Total distance in nautical miles
        """
        total_distance = 0
        for i in range(len(waypoints) - 1):
            total_distance += self.calculate_distance(waypoints[i], waypoints[i + 1])
        return total_distance
    
    def estimate_fuel_consumption(
        self,
        flight_plan: FlightPlan,
        weather_data: List[WeatherCondition],
        altitude: int
    ) -> Dict:
        """
        Estimate fuel consumption for a flight
        
        Args:
            flight_plan: Flight plan details
            weather_data: Weather conditions along route
            altitude: Cruise altitude
            
        Returns:
            Dict with fuel consumption details
        """
        # Get aircraft performance data
        aircraft = self.AIRCRAFT_DB.get(
            flight_plan.aircraft_type,
            self.AIRCRAFT_DB["B737-800"]  # Default
        )
        
        # Calculate route distance
        distance = self.calculate_route_distance(flight_plan.route_waypoints)
        
        # Base fuel burn rate
        fuel_burn_rate = aircraft.fuel_burn_rate_base
        
        # Altitude adjustment (optimal altitude = 1.0, others increase fuel burn)
        altitude_factor = self._calculate_altitude_factor(altitude, aircraft.optimal_cruise_altitude)
        fuel_burn_rate *= altitude_factor
        
        # Weight adjustment (heavier = more fuel)
        total_weight = aircraft.weight_empty + flight_plan.cargo_weight + (flight_plan.passenger_count * 90)
        weight_factor = 1 + ((total_weight - aircraft.weight_empty) / aircraft.weight_empty) * 0.15
        fuel_burn_rate *= weight_factor
        
        # Wind adjustment
        avg_wind_impact = self._calculate_wind_impact(flight_plan, weather_data)
        
        # Calculate flight time
        ground_speed = aircraft.cruise_speed + avg_wind_impact  # +tailwind or -headwind
        flight_time_hours = distance / ground_speed
        
        # Total fuel
        total_fuel = fuel_burn_rate * flight_time_hours
        
        # Add reserves (5% contingency + 30 min holding)
        reserve_fuel = total_fuel * 0.05 + (fuel_burn_rate * 0.5)
        total_fuel_with_reserves = total_fuel + reserve_fuel
        
        return {
            "distance_nm": round(distance, 1),
            "flight_time_hours": round(flight_time_hours, 2),
            "fuel_burn_rate": round(fuel_burn_rate, 1),
            "cruise_fuel": round(total_fuel, 1),
            "reserve_fuel": round(reserve_fuel, 1),
            "total_fuel": round(total_fuel_with_reserves, 1),
            "altitude_factor": round(altitude_factor, 3),
            "weight_factor": round(weight_factor, 3),
            "avg_wind_impact": round(avg_wind_impact, 1),
            "ground_speed": round(ground_speed, 1)
        }
    
    def optimize_flight(self, flight_plan: FlightPlan) -> OptimizationResult:
        """
        Perform comprehensive flight optimization
        
        Args:
            flight_plan: Original flight plan
            
        Returns:
            Optimization result with recommendations
        """
        logger.info(f"Optimizing flight {flight_plan.flight_id}")
        
        # Fetch weather data
        weather_data = self.weather_service.fetch_weather_for_route(flight_plan.route_waypoints)
        
        # Calculate original fuel consumption
        original_fuel_calc = self.estimate_fuel_consumption(
            flight_plan,
            weather_data,
            flight_plan.cruise_altitude
        )
        original_fuel = original_fuel_calc["total_fuel"]
        
        # Test alternative altitudes
        altitude_options = [32000, 34000, 36000, 38000, 40000]
        best_altitude = flight_plan.cruise_altitude
        best_altitude_fuel = original_fuel
        
        for alt in altitude_options:
            fuel_calc = self.estimate_fuel_consumption(flight_plan, weather_data, alt)
            if fuel_calc["total_fuel"] < best_altitude_fuel:
                best_altitude = alt
                best_altitude_fuel = fuel_calc["total_fuel"]
        
        # Analyze jet stream
        jet_stream = self.weather_service.get_jet_stream_info(
            flight_plan.route_waypoints,
            best_altitude
        )
        
        # Calculate optimized fuel
        optimized_fuel_calc = self.estimate_fuel_consumption(
            flight_plan,
            weather_data,
            best_altitude
        )
        optimized_fuel = optimized_fuel_calc["total_fuel"]
        
        # Determine recommendation type
        altitude_change = abs(best_altitude - flight_plan.cruise_altitude)
        if altitude_change >= 4000:
            rec_type = RecommendationType.ALTITUDE_OPTIMIZATION
        else:
            rec_type = RecommendationType.ROUTE_MODIFICATION
        
        # Calculate savings
        fuel_savings = original_fuel - optimized_fuel
        savings_percentage = (fuel_savings / original_fuel) * 100
        
        # Build rationale
        rationale_parts = []
        if altitude_change >= 2000:
            rationale_parts.append(
                f"Altitude change from FL{flight_plan.cruise_altitude//100} to "
                f"FL{best_altitude//100} optimizes fuel efficiency"
            )
        
        if jet_stream.get("present"):
            rationale_parts.append(f"Jet stream analysis: {jet_stream['benefit']}")
        
        if optimized_fuel_calc["avg_wind_impact"] > 0:
            rationale_parts.append(
                f"Favorable tailwind component of {optimized_fuel_calc['avg_wind_impact']:.0f} knots"
            )
        
        rationale = ". ".join(rationale_parts) if rationale_parts else "Standard optimization applied"
        
        # Weather factors
        weather_factors = []
        if jet_stream.get("present"):
            weather_factors.append(f"Jet stream: {jet_stream['strength']} {jet_stream['direction']}")
        
        avg_wind = sum(w.wind_speed for w in weather_data) / len(weather_data) if weather_data else 0
        if avg_wind > 100:
            weather_factors.append(f"Strong winds averaging {avg_wind:.0f} knots")
        
        # Confidence score based on weather data quality and savings magnitude
        confidence = min(0.95, 0.70 + (savings_percentage / 100))
        
        # Time impact (minimal for altitude changes)
        time_impact = 0
        if altitude_change >= 4000:
            time_impact = 2  # Small delay for altitude change coordination
        
        return OptimizationResult(
            flight_id=flight_plan.flight_id,
            original_fuel=original_fuel,
            optimized_fuel=optimized_fuel,
            fuel_savings=fuel_savings,
            savings_percentage=savings_percentage,
            time_impact=time_impact,
            confidence_score=confidence,
            recommendation_type=rec_type,
            optimized_altitude=best_altitude,
            rationale=rationale,
            weather_factors=weather_factors,
            cost_savings=fuel_savings * self.FUEL_PRICE_PER_KG
        )
    
    def _calculate_altitude_factor(self, altitude: int, optimal_altitude: int) -> float:
        """Calculate fuel burn factor based on altitude deviation"""
        deviation = abs(altitude - optimal_altitude)
        # Each 2000 ft deviation increases fuel burn by ~1.5%
        factor = 1.0 + (deviation / 2000) * 0.015
        return factor
    
    def _calculate_wind_impact(
        self,
        flight_plan: FlightPlan,
        weather_data: List[WeatherCondition]
    ) -> float:
        """Calculate average wind impact on ground speed"""
        if not weather_data:
            return 0
        
        # Calculate course for each leg
        total_impact = 0
        for i, weather in enumerate(weather_data):
            if i < len(flight_plan.route_waypoints) - 1:
                # Simplified: assume general direction
                # Positive = tailwind, Negative = headwind
                wind_component = weather.wind_speed * 0.5  # Simplified calculation
                if weather.wind_direction > 180:
                    wind_component = -wind_component
                total_impact += wind_component
        
        return total_impact / len(weather_data) if weather_data else 0
