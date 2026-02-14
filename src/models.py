"""
Data models for the Airline Fuel Optimization Agent
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class RecommendationType(str, Enum):
    """Types of optimization recommendations"""
    ROUTE_MODIFICATION = "route_modification"
    ALTITUDE_OPTIMIZATION = "altitude_optimization"
    DELAY_RECOMMENDATION = "delay_recommendation"
    RE_DISPATCH = "re_dispatch"


class Waypoint(BaseModel):
    """Flight waypoint with coordinates"""
    name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[int] = None  # feet


class WeatherCondition(BaseModel):
    """Weather data for a specific location"""
    location: str
    timestamp: datetime
    temperature: float  # Celsius
    wind_speed: int  # knots
    wind_direction: int  # degrees
    visibility: float  # statute miles
    conditions: str
    metar_raw: Optional[str] = None


class AircraftPerformance(BaseModel):
    """Aircraft performance characteristics"""
    aircraft_type: str
    max_cruise_altitude: int = 41000  # feet
    optimal_cruise_altitude: int = 36000  # feet
    cruise_speed: int = 450  # knots
    fuel_capacity: int = 26000  # kg
    fuel_burn_rate_base: float = 2400  # kg/hour at optimal conditions
    weight_empty: int = 42000  # kg
    max_payload: int = 20000  # kg


class FlightPlan(BaseModel):
    """Complete flight plan data"""
    flight_id: str
    origin: str
    destination: str
    aircraft_type: str
    departure_time: datetime
    route_waypoints: List[Waypoint]
    planned_fuel: float  # kg
    cruise_altitude: int = 36000  # feet
    estimated_duration: int = 300  # minutes
    passenger_count: int = 150
    cargo_weight: int = 5000  # kg


class OptimizationResult(BaseModel):
    """Result of fuel optimization analysis"""
    flight_id: str
    original_fuel: float  # kg
    optimized_fuel: float  # kg
    fuel_savings: float  # kg
    savings_percentage: float
    time_impact: int  # minutes (can be negative)
    confidence_score: float = Field(..., ge=0, le=1)
    recommendation_type: RecommendationType
    optimized_route: Optional[List[Waypoint]] = None
    optimized_altitude: Optional[int] = None
    rationale: str
    weather_factors: List[str] = []
    cost_savings: Optional[float] = None  # USD


class OptimizationRecommendation(BaseModel):
    """Formatted recommendation for operations team"""
    flight_id: str
    recommendation_type: RecommendationType
    priority: str  # "high", "medium", "low"
    action_required: str
    expected_fuel_savings: float  # kg
    expected_cost_savings: float  # USD
    time_impact: int  # minutes
    confidence_level: float
    weather_considerations: List[str]
    implementation_steps: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MCPMessage(BaseModel):
    """Message format for MCP integration"""
    message_id: str
    message_type: str
    flight_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict
    priority: int = 5  # 1-10, 10 being highest
    requires_acknowledgment: bool = True
