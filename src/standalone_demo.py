"""
Standalone Airline Fuel Optimization Agent Demo
Simplified version without external dependencies for demonstration
"""
import json
import csv
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


# ==================== DATA MODELS ====================

@dataclass
class Waypoint:
    """Flight waypoint with coordinates"""
    name: str
    latitude: float
    longitude: float
    altitude: Optional[int] = None


@dataclass
class WeatherCondition:
    """Weather data for a location"""
    location: str
    timestamp: str
    temperature: float
    wind_speed: int
    wind_direction: int
    visibility: float
    conditions: str


@dataclass
class FlightPlan:
    """Complete flight plan"""
    flight_id: str
    origin: str
    destination: str
    aircraft_type: str
    departure_time: str
    route_waypoints: List[Waypoint]
    planned_fuel: float
    cruise_altitude: int
    passenger_count: int = 150
    cargo_weight: int = 5000


@dataclass
class OptimizationResult:
    """Optimization result"""
    flight_id: str
    original_fuel: float
    optimized_fuel: float
    fuel_savings: float
    savings_percentage: float
    time_impact: int
    confidence_score: float
    recommendation_type: str
    optimized_altitude: int
    rationale: str
    weather_factors: List[str]
    cost_savings: float


# ==================== WEATHER SERVICE ====================

class WeatherService:
    """Simple weather service with mock data"""
    
    def fetch_weather_for_route(self, waypoints: List[Waypoint]) -> List[WeatherCondition]:
        """Generate mock weather for waypoints"""
        import random
        
        weather_data = []
        for wp in waypoints:
            base_temp = 15 - (wp.latitude / 10)
            
            weather_data.append(WeatherCondition(
                location=wp.name,
                timestamp=datetime.utcnow().isoformat(),
                temperature=round(base_temp + random.uniform(-10, 10), 1),
                wind_speed=random.choice([50, 75, 100, 125, 150]),
                wind_direction=random.choice([270, 280, 290, 300]),
                visibility=10.0,
                conditions=random.choice(["Clear", "Few Clouds", "Scattered Clouds"])
            ))
        
        return weather_data


# ==================== OPTIMIZATION ENGINE ====================

class FuelOptimizationEngine:
    """Core fuel optimization logic"""
    
    FUEL_PRICE_PER_KG = 0.85
    
    AIRCRAFT_DB = {
        "B737-800": {"optimal_alt": 36000, "burn_rate": 2400, "speed": 450},
        "A320": {"optimal_alt": 35000, "burn_rate": 2300, "speed": 447},
        "B777-300": {"optimal_alt": 38000, "burn_rate": 7500, "speed": 490}
    }
    
    def __init__(self, weather_service: WeatherService):
        self.weather_service = weather_service
    
    def calculate_distance(self, point1: Waypoint, point2: Waypoint) -> float:
        """Calculate great circle distance in nautical miles"""
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return c * 3440.065  # Earth radius in nautical miles
    
    def calculate_route_distance(self, waypoints: List[Waypoint]) -> float:
        """Calculate total route distance"""
        total = 0
        for i in range(len(waypoints) - 1):
            total += self.calculate_distance(waypoints[i], waypoints[i + 1])
        return total
    
    def estimate_fuel(self, flight_plan: FlightPlan, altitude: int, weather: List[WeatherCondition]) -> float:
        """Estimate fuel consumption"""
        aircraft = self.AIRCRAFT_DB.get(flight_plan.aircraft_type, self.AIRCRAFT_DB["B737-800"])
        
        distance = self.calculate_route_distance(flight_plan.route_waypoints)
        burn_rate = aircraft["burn_rate"]
        
        # Altitude factor
        alt_deviation = abs(altitude - aircraft["optimal_alt"])
        burn_rate *= (1.0 + (alt_deviation / 2000) * 0.015)
        
        # Wind impact (simplified)
        avg_wind = sum(w.wind_speed for w in weather) / len(weather) if weather else 0
        wind_impact = avg_wind * 0.3  # Simplified tailwind benefit
        
        # Calculate flight time and fuel
        ground_speed = aircraft["speed"] + wind_impact
        flight_time = distance / ground_speed
        total_fuel = burn_rate * flight_time
        
        # Add 5% reserves
        return total_fuel * 1.05
    
    def optimize_flight(self, flight_plan: FlightPlan) -> OptimizationResult:
        """Perform fuel optimization"""
        print(f"  → Analyzing weather...")
        weather = self.weather_service.fetch_weather_for_route(flight_plan.route_waypoints)
        
        print(f"  → Testing altitude scenarios...")
        original_fuel = self.estimate_fuel(flight_plan, flight_plan.cruise_altitude, weather)
        
        # Test alternative altitudes
        altitudes = [32000, 34000, 36000, 38000, 40000]
        best_alt = flight_plan.cruise_altitude
        best_fuel = original_fuel
        
        for alt in altitudes:
            fuel = self.estimate_fuel(flight_plan, alt, weather)
            if fuel < best_fuel:
                best_alt = alt
                best_fuel = fuel
        
        print(f"  → Computing optimal recommendation...")
        fuel_savings = original_fuel - best_fuel
        savings_pct = (fuel_savings / original_fuel) * 100
        
        # Build rationale
        rationale_parts = []
        if abs(best_alt - flight_plan.cruise_altitude) >= 2000:
            rationale_parts.append(
                f"Altitude change from FL{flight_plan.cruise_altitude//100} to FL{best_alt//100}"
            )
        
        avg_wind = sum(w.wind_speed for w in weather) / len(weather) if weather else 0
        if avg_wind > 100:
            rationale_parts.append(f"Favorable winds averaging {avg_wind:.0f} knots")
        
        rationale = ". ".join(rationale_parts) if rationale_parts else "Standard optimization"
        
        weather_factors = []
        if avg_wind > 100:
            weather_factors.append(f"Strong westerly winds: {avg_wind:.0f} knots")
        
        confidence = min(0.95, 0.70 + (savings_pct / 100))
        
        rec_type = "altitude_optimization" if abs(best_alt - flight_plan.cruise_altitude) >= 4000 else "route_modification"
        
        return OptimizationResult(
            flight_id=flight_plan.flight_id,
            original_fuel=original_fuel,
            optimized_fuel=best_fuel,
            fuel_savings=fuel_savings,
            savings_percentage=savings_pct,
            time_impact=2 if rec_type == "altitude_optimization" else 0,
            confidence_score=confidence,
            recommendation_type=rec_type,
            optimized_altitude=best_alt,
            rationale=rationale,
            weather_factors=weather_factors,
            cost_savings=fuel_savings * self.FUEL_PRICE_PER_KG
        )


# ==================== MAIN APPLICATION ====================

class FuelOptimizationAgent:
    """Main application"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.weather_service = WeatherService()
        self.optimization_engine = FuelOptimizationEngine(self.weather_service)
        self.results = []
    
    def load_data(self):
        """Load flight and route data"""
        flights = []
        csv_path = self.data_dir / "sample_flights.csv"
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            flights = list(reader)
        
        with open(self.data_dir / "route_waypoints.json", 'r') as f:
            routes = json.load(f)
        
        return flights, routes
    
    def create_flight_plan(self, flight_data: dict, routes: dict) -> FlightPlan:
        """Create flight plan from data"""
        flight_id = flight_data['flight_id']
        waypoints = [
            Waypoint(**wp) for wp in routes.get(flight_id, {}).get('route', [])
        ]
        
        return FlightPlan(
            flight_id=flight_id,
            origin=flight_data['origin'],
            destination=flight_data['destination'],
            aircraft_type=flight_data['aircraft_type'],
            departure_time=flight_data['departure_time'],
            route_waypoints=waypoints,
            planned_fuel=float(flight_data['planned_fuel']),
            cruise_altitude=int(flight_data['cruise_altitude']),
            passenger_count=int(flight_data['passenger_count']),
            cargo_weight=int(flight_data['cargo_weight'])
        )
    
    def run_optimization(self):
        """Run batch optimization"""
        print("\n" + "=" * 60)
        print("AIRLINE FUEL OPTIMIZATION AGENT")
        print("Powered by AWS Strands and MCP")
        print("=" * 60 + "\n")
        
        flights, routes = self.load_data()
        
        print(f"Loaded {len(flights)} flights for optimization\n")
        
        for flight_data in flights:
            print(f"Processing {flight_data['flight_id']}...")
            
            flight_plan = self.create_flight_plan(flight_data, routes)
            result = self.optimization_engine.optimize_flight(flight_plan)
            self.results.append(result)
            
            print(f"\n✈️  {flight_plan.flight_id}: {flight_plan.origin} → {flight_plan.destination}")
            print(f"   Fuel Savings: {result.fuel_savings:.1f} kg ({result.savings_percentage:.1f}%)")
            print(f"   Cost Savings: ${result.cost_savings:.2f}")
            print(f"   Recommendation: {result.recommendation_type.replace('_', ' ').title()}")
            print(f"   Confidence: {result.confidence_score * 100:.0f}%\n")
        
        self.generate_report()
    
    def generate_report(self):
        """Generate summary report"""
        total_fuel_savings = sum(r.fuel_savings for r in self.results)
        total_cost_savings = sum(r.cost_savings for r in self.results)
        avg_confidence = sum(r.confidence_score for r in self.results) / len(self.results)
        high_priority = sum(1 for r in self.results if r.savings_percentage >= 3)
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_flights": len(self.results),
            "summary": {
                "total_fuel_savings_kg": round(total_fuel_savings, 1),
                "total_cost_savings_usd": round(total_cost_savings, 2),
                "average_confidence": round(avg_confidence, 3),
                "high_priority_recommendations": high_priority
            },
            "flights": [asdict(r) for r in self.results]
        }
        
        # Save report
        with open('optimization_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "=" * 60)
        print("OPTIMIZATION SUMMARY")
        print("=" * 60)
        print(f"Total Flights Processed: {len(self.results)}")
        print(f"Total Fuel Savings: {total_fuel_savings:.1f} kg")
        print(f"Total Cost Savings: ${total_cost_savings:.2f}")
        print(f"High Priority Actions: {high_priority}")
        print(f"Average Confidence: {avg_confidence * 100:.0f}%")
        print("=" * 60)
        print(f"\n✅ Report saved to: optimization_report.json\n")


if __name__ == "__main__":
    agent = FuelOptimizationAgent(data_dir="../data")
    agent.run_optimization()
