"""
Main application for Airline Fuel Optimization Agent
Orchestrates the complete optimization workflow
"""
import json
import logging
import csv
from datetime import datetime
from pathlib import Path
from typing import List

from models import FlightPlan, Waypoint
from weather_service import WeatherService
from optimization_engine import FuelOptimizationEngine
from strands_orchestrator import StrandsOrchestrator, WorkflowState
from mcp_integration import MCPIntegration, MCPMessageFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FuelOptimizationAgent:
    """Main application class for fuel optimization"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the fuel optimization agent
        
        Args:
            data_dir: Directory containing input data files
        """
        self.data_dir = Path(data_dir)
        
        # Initialize components
        self.weather_service = WeatherService()
        self.optimization_engine = FuelOptimizationEngine(self.weather_service)
        self.orchestrator = StrandsOrchestrator()
        self.mcp_integration = MCPIntegration()
        
        logger.info("Fuel Optimization Agent initialized")
    
    def load_flight_data(self, csv_file: str = "sample_flights.csv") -> List[dict]:
        """
        Load flight data from CSV file
        
        Args:
            csv_file: CSV filename
            
        Returns:
            List of flight data dictionaries
        """
        flights = []
        csv_path = self.data_dir / csv_file
        
        logger.info(f"Loading flight data from {csv_path}")
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                flights.append(row)
        
        logger.info(f"Loaded {len(flights)} flights")
        return flights
    
    def load_route_waypoints(self, json_file: str = "route_waypoints.json") -> dict:
        """
        Load route waypoints from JSON file
        
        Args:
            json_file: JSON filename
            
        Returns:
            Dictionary of flight routes
        """
        json_path = self.data_dir / json_file
        
        logger.info(f"Loading route waypoints from {json_path}")
        
        with open(json_path, 'r') as f:
            routes = json.load(f)
        
        logger.info(f"Loaded routes for {len(routes)} flights")
        return routes
    
    def create_flight_plan(self, flight_data: dict, route_data: dict) -> FlightPlan:
        """
        Create FlightPlan object from raw data
        
        Args:
            flight_data: Flight information from CSV
            route_data: Route waypoints data
            
        Returns:
            FlightPlan object
        """
        flight_id = flight_data['flight_id']
        
        # Get route waypoints
        route_waypoints = [
            Waypoint(**wp) for wp in route_data.get(flight_id, {}).get('route', [])
        ]
        
        # Create flight plan
        return FlightPlan(
            flight_id=flight_id,
            origin=flight_data['origin'],
            destination=flight_data['destination'],
            aircraft_type=flight_data['aircraft_type'],
            departure_time=datetime.fromisoformat(flight_data['departure_time']),
            route_waypoints=route_waypoints,
            planned_fuel=float(flight_data['planned_fuel']),
            cruise_altitude=int(flight_data['cruise_altitude']),
            passenger_count=int(flight_data['passenger_count']),
            cargo_weight=int(flight_data['cargo_weight'])
        )
    
    def process_single_flight(self, flight_plan: FlightPlan) -> dict:
        """
        Process a single flight through the optimization workflow
        
        Args:
            flight_plan: Flight plan to optimize
            
        Returns:
            Complete optimization results
        """
        logger.info(f"Processing flight {flight_plan.flight_id}")
        
        # Reset orchestrator
        self.orchestrator.reset_workflow()
        
        # Step 1: Data Ingestion
        workflow_data = {"flight_plan": flight_plan.dict()}
        result = self.orchestrator.execute_workflow_step(
            WorkflowState.DATA_INGESTION,
            workflow_data
        )
        
        # Step 2: Weather Analysis
        weather_data = self.weather_service.fetch_weather_for_route(flight_plan.route_waypoints)
        workflow_data["weather_data"] = [w.dict() for w in weather_data]
        result = self.orchestrator.execute_workflow_step(
            WorkflowState.WEATHER_ANALYSIS,
            workflow_data
        )
        
        # Step 3: Optimization Compute
        optimization_result = self.optimization_engine.optimize_flight(flight_plan)
        workflow_data["optimization_result"] = optimization_result.dict()
        result = self.orchestrator.execute_workflow_step(
            WorkflowState.OPTIMIZATION_COMPUTE,
            workflow_data
        )
        
        # Step 4: Recommendation Generation
        recommendation = self.mcp_integration.create_recommendation_message(optimization_result)
        workflow_data["recommendations"] = recommendation.dict()
        result = self.orchestrator.execute_workflow_step(
            WorkflowState.RECOMMENDATION_GENERATION,
            workflow_data
        )
        
        # Step 5: Results Publication
        publication_result = self.mcp_integration.publish_to_operations(recommendation)
        workflow_data["publication"] = publication_result
        result = self.orchestrator.execute_workflow_step(
            WorkflowState.RESULTS_PUBLICATION,
            workflow_data
        )
        
        # Get workflow status
        workflow_status = self.orchestrator.get_workflow_status()
        
        return {
            "flight_id": flight_plan.flight_id,
            "optimization_result": optimization_result.dict(),
            "recommendation": recommendation.dict(),
            "publication": publication_result,
            "workflow_status": workflow_status
        }
    
    def generate_report(self, results: List[dict], output_file: str = "optimization_report.json"):
        """
        Generate comprehensive optimization report
        
        Args:
            results: List of optimization results
            output_file: Output filename
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_flights": len(results),
            "summary": self._generate_summary(results),
            "flights": results
        }
        
        output_path = self.data_dir.parent / output_file
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report generated: {output_path}")
        return report
    
    def _generate_summary(self, results: List[dict]) -> dict:
        """Generate summary statistics from results"""
        total_fuel_savings = sum(
            r['optimization_result']['fuel_savings'] for r in results
        )
        total_cost_savings = sum(
            r['optimization_result']['cost_savings'] for r in results
        )
        avg_confidence = sum(
            r['optimization_result']['confidence_score'] for r in results
        ) / len(results)
        
        high_priority = sum(
            1 for r in results if r['recommendation']['priority'] == 'high'
        )
        
        return {
            "total_fuel_savings_kg": round(total_fuel_savings, 1),
            "total_cost_savings_usd": round(total_cost_savings, 2),
            "average_confidence": round(avg_confidence, 3),
            "high_priority_recommendations": high_priority,
            "optimization_rate": f"{(len(results) / len(results)) * 100:.0f}%"
        }
    
    def run_batch_optimization(self):
        """
        Run optimization for all flights in the data directory
        
        Returns:
            Optimization report
        """
        logger.info("Starting batch optimization")
        
        # Load data
        flights = self.load_flight_data()
        routes = self.load_route_waypoints()
        
        # Process each flight
        results = []
        for flight_data in flights:
            try:
                flight_plan = self.create_flight_plan(flight_data, routes)
                result = self.process_single_flight(flight_plan)
                results.append(result)
                
                # Print summary
                opt_result = result['optimization_result']
                print(f"\n✈️  {flight_plan.flight_id}: {flight_plan.origin} → {flight_plan.destination}")
                print(f"   Fuel Savings: {opt_result['fuel_savings']:.1f} kg ({opt_result['savings_percentage']:.1f}%)")
                print(f"   Cost Savings: ${opt_result['cost_savings']:.2f}")
                print(f"   Recommendation: {opt_result['recommendation_type']}")
                print(f"   Confidence: {opt_result['confidence_score'] * 100:.0f}%")
                
            except Exception as e:
                logger.error(f"Error processing flight {flight_data['flight_id']}: {e}")
        
        # Generate report
        report = self.generate_report(results)
        
        print("\n" + "=" * 60)
        print("OPTIMIZATION SUMMARY")
        print("=" * 60)
        print(f"Total Flights Processed: {report['summary']['optimization_rate']}")
        print(f"Total Fuel Savings: {report['summary']['total_fuel_savings_kg']:.1f} kg")
        print(f"Total Cost Savings: ${report['summary']['total_cost_savings_usd']:.2f}")
        print(f"High Priority Actions: {report['summary']['high_priority_recommendations']}")
        print(f"Average Confidence: {report['summary']['average_confidence'] * 100:.0f}%")
        print("=" * 60)
        
        return report


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("AIRLINE FUEL OPTIMIZATION AGENT")
    print("Powered by AWS Strands and MCP")
    print("=" * 60 + "\n")
    
    # Initialize agent
    agent = FuelOptimizationAgent(data_dir="data")
    
    # Run batch optimization
    report = agent.run_batch_optimization()
    
    print(f"\n✅ Complete! Report saved to: optimization_report.json\n")


if __name__ == "__main__":
    main()
