"""
AWS Lambda Handler for Fuel Optimization
Serverless entry point for the optimization system
"""
import json
import logging
from typing import Dict, Any

# Import our modules
import sys
sys.path.append('/opt')  # Lambda layer path

from models import FlightPlan, Waypoint
from weather_service import WeatherService
from optimization_engine import FuelOptimizationEngine
from mcp_integration import MCPIntegration

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize services (will be reused across warm starts)
weather_service = WeatherService()
optimization_engine = FuelOptimizationEngine(weather_service)
mcp_integration = MCPIntegration()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for fuel optimization
    
    Expected event format:
    {
        "flight_id": "AA1234",
        "origin": "JFK",
        "destination": "LAX",
        "aircraft_type": "B737-800",
        "departure_time": "2025-02-15T14:30:00",
        "cruise_altitude": 36000,
        "planned_fuel": 15000,
        "waypoints": [
            {"name": "JFK", "latitude": 40.64, "longitude": -73.78},
            ...
        ]
    }
    
    Returns:
        Optimization result and recommendation
    """
    try:
        logger.info(f"Processing event: {json.dumps(event)}")
        
        # Parse flight plan from event
        flight_plan = parse_flight_plan(event)
        
        # Run optimization
        optimization_result = optimization_engine.optimize_flight(flight_plan)
        
        # Create recommendation
        recommendation = mcp_integration.create_recommendation_message(optimization_result)
        
        # Publish to MCP (SQS/SNS)
        publication_result = mcp_integration.publish_to_operations(recommendation)
        
        # Return response
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "flight_id": flight_plan.flight_id,
                "optimization": optimization_result.dict(),
                "recommendation": recommendation.dict(),
                "publication": publication_result
            })
        }
        
        logger.info(f"Successfully processed flight {flight_plan.flight_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing flight: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "Failed to process flight optimization"
            })
        }


def parse_flight_plan(event: Dict[str, Any]) -> FlightPlan:
    """Parse FlightPlan from Lambda event"""
    from datetime import datetime
    
    waypoints = [Waypoint(**wp) for wp in event.get('waypoints', [])]
    
    return FlightPlan(
        flight_id=event['flight_id'],
        origin=event['origin'],
        destination=event['destination'],
        aircraft_type=event['aircraft_type'],
        departure_time=datetime.fromisoformat(event['departure_time']),
        route_waypoints=waypoints,
        planned_fuel=event.get('planned_fuel', 15000),
        cruise_altitude=event.get('cruise_altitude', 36000),
        passenger_count=event.get('passenger_count', 150),
        cargo_weight=event.get('cargo_weight', 5000)
    )


# Handler for Step Functions state machine steps
def data_ingestion_handler(event: Dict, context: Any) -> Dict:
    """Handler for data ingestion step"""
    logger.info("Executing data ingestion step")
    return {
        "statusCode": 200,
        "step": "data_ingestion",
        "data": event,
        "validation": "passed"
    }


def weather_analysis_handler(event: Dict, context: Any) -> Dict:
    """Handler for weather analysis step"""
    logger.info("Executing weather analysis step")
    
    waypoints = [Waypoint(**wp) for wp in event.get('waypoints', [])]
    weather_data = weather_service.fetch_weather_for_route(waypoints)
    
    return {
        "statusCode": 200,
        "step": "weather_analysis",
        "weather_data": [w.dict() for w in weather_data]
    }


def optimization_compute_handler(event: Dict, context: Any) -> Dict:
    """Handler for optimization computation step"""
    logger.info("Executing optimization compute step")
    
    flight_plan = parse_flight_plan(event)
    optimization_result = optimization_engine.optimize_flight(flight_plan)
    
    return {
        "statusCode": 200,
        "step": "optimization_compute",
        "result": optimization_result.dict()
    }


def recommendation_generation_handler(event: Dict, context: Any) -> Dict:
    """Handler for recommendation generation step"""
    logger.info("Executing recommendation generation step")
    
    from models import OptimizationResult
    opt_result = OptimizationResult(**event['result'])
    recommendation = mcp_integration.create_recommendation_message(opt_result)
    
    return {
        "statusCode": 200,
        "step": "recommendation_generation",
        "recommendation": recommendation.dict()
    }


def results_publication_handler(event: Dict, context: Any) -> Dict:
    """Handler for results publication step"""
    logger.info("Executing results publication step")
    
    from models import OptimizationRecommendation
    recommendation = OptimizationRecommendation(**event['recommendation'])
    publication_result = mcp_integration.publish_to_operations(recommendation)
    
    return {
        "statusCode": 200,
        "step": "results_publication",
        "publication": publication_result
    }
