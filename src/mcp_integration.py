"""
MCP (Model Context Protocol) Integration
Handles communication with airline operational systems
"""
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from models import MCPMessage, OptimizationRecommendation, OptimizationResult

logger = logging.getLogger(__name__)


class MCPIntegration:
    """
    Integration layer for MCP protocol
    Publishes recommendations to operational systems via message queues
    """
    
    def __init__(self, queue_url: Optional[str] = None, sns_topic_arn: Optional[str] = None):
        """
        Initialize MCP integration
        
        Args:
            queue_url: SQS queue URL for publishing messages
            sns_topic_arn: SNS topic ARN for notifications
        """
        self.queue_url = queue_url or "mock-queue-url"
        self.sns_topic_arn = sns_topic_arn or "mock-sns-topic"
        self.message_history = []
        
    def create_recommendation_message(
        self,
        optimization_result: OptimizationResult
    ) -> OptimizationRecommendation:
        """
        Create a formatted recommendation from optimization result
        
        Args:
            optimization_result: Optimization result data
            
        Returns:
            Formatted recommendation
        """
        # Determine priority based on savings
        if optimization_result.savings_percentage >= 5:
            priority = "high"
        elif optimization_result.savings_percentage >= 2:
            priority = "medium"
        else:
            priority = "low"
        
        # Create action steps
        implementation_steps = self._generate_implementation_steps(optimization_result)
        
        # Format action required
        action_required = self._format_action_required(optimization_result)
        
        return OptimizationRecommendation(
            flight_id=optimization_result.flight_id,
            recommendation_type=optimization_result.recommendation_type,
            priority=priority,
            action_required=action_required,
            expected_fuel_savings=optimization_result.fuel_savings,
            expected_cost_savings=optimization_result.cost_savings or 0,
            time_impact=optimization_result.time_impact,
            confidence_level=optimization_result.confidence_score,
            weather_considerations=optimization_result.weather_factors,
            implementation_steps=implementation_steps
        )
    
    def publish_to_operations(
        self,
        recommendation: OptimizationRecommendation
    ) -> Dict[str, Any]:
        """
        Publish recommendation to operations team via MCP
        
        Args:
            recommendation: Optimization recommendation
            
        Returns:
            Publication result
        """
        # Create MCP message
        mcp_message = MCPMessage(
            message_id=str(uuid.uuid4()),
            message_type="fuel_optimization_recommendation",
            flight_id=recommendation.flight_id,
            payload=recommendation.dict(),
            priority=self._priority_to_int(recommendation.priority),
            requires_acknowledgment=True
        )
        
        logger.info(f"Publishing MCP message {mcp_message.message_id} for flight {recommendation.flight_id}")
        
        # In production, this would publish to SQS/SNS
        # For demo, we'll simulate the publication
        result = self._simulate_publish(mcp_message)
        
        # Store in history
        self.message_history.append({
            "message_id": mcp_message.message_id,
            "flight_id": recommendation.flight_id,
            "timestamp": datetime.utcnow().isoformat(),
            "priority": recommendation.priority,
            "status": result["status"]
        })
        
        return result
    
    def _simulate_publish(self, message: MCPMessage) -> Dict[str, Any]:
        """
        Simulate message publication (for demo purposes)
        In production, this would use boto3 to publish to SQS/SNS
        
        Args:
            message: MCP message to publish
            
        Returns:
            Publication result
        """
        # Simulated AWS SQS/SNS response
        return {
            "status": "published",
            "message_id": message.message_id,
            "queue_url": self.queue_url,
            "timestamp": datetime.utcnow().isoformat(),
            "receipt_handle": f"mock-receipt-{message.message_id[:8]}"
        }
    
    def _generate_implementation_steps(self, result: OptimizationResult) -> list:
        """Generate implementation steps based on recommendation type"""
        steps = []
        
        if result.recommendation_type.value == "altitude_optimization":
            steps = [
                "1. Review current flight plan and fuel calculations",
                f"2. Request altitude change to FL{result.optimized_altitude // 100} from ATC",
                "3. Update FMS with new cruise altitude",
                "4. Monitor fuel consumption after altitude change",
                "5. Report actual savings to operations"
            ]
        elif result.recommendation_type.value == "route_modification":
            steps = [
                "1. Review proposed route modifications",
                "2. Verify route changes with dispatch",
                "3. Submit route amendment request to ATC",
                "4. Update FMS with new waypoints",
                "5. Monitor progress and fuel consumption"
            ]
        else:
            steps = [
                "1. Review optimization recommendation",
                "2. Coordinate with dispatch and ATC",
                "3. Implement approved changes",
                "4. Monitor and report results"
            ]
        
        return steps
    
    def _format_action_required(self, result: OptimizationResult) -> str:
        """Format action required text"""
        if result.recommendation_type.value == "altitude_optimization":
            return f"Request altitude change to FL{result.optimized_altitude // 100} for {result.fuel_savings:.0f}kg fuel savings"
        elif result.recommendation_type.value == "route_modification":
            return f"Review route modifications for {result.fuel_savings:.0f}kg fuel savings"
        else:
            return f"Implement optimization for {result.fuel_savings:.0f}kg fuel savings"
    
    def _priority_to_int(self, priority: str) -> int:
        """Convert priority string to integer"""
        priority_map = {
            "low": 3,
            "medium": 6,
            "high": 9
        }
        return priority_map.get(priority.lower(), 5)
    
    def get_message_history(self) -> list:
        """Get publication history"""
        return self.message_history
    
    def acknowledge_message(self, message_id: str) -> Dict[str, Any]:
        """
        Acknowledge message receipt (simulated)
        
        Args:
            message_id: Message ID to acknowledge
            
        Returns:
            Acknowledgment result
        """
        return {
            "status": "acknowledged",
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }


class MCPMessageFormatter:
    """Utility class for formatting MCP messages"""
    
    @staticmethod
    def format_for_dashboard(recommendation: OptimizationRecommendation) -> Dict:
        """Format recommendation for dashboard display"""
        return {
            "flight": recommendation.flight_id,
            "type": recommendation.recommendation_type.value.replace("_", " ").title(),
            "priority": recommendation.priority.upper(),
            "savings": {
                "fuel_kg": round(recommendation.expected_fuel_savings, 1),
                "cost_usd": round(recommendation.expected_cost_savings, 2),
                "percentage": f"{(recommendation.expected_fuel_savings / 15000) * 100:.1f}%"
            },
            "confidence": f"{recommendation.confidence_level * 100:.0f}%",
            "action": recommendation.action_required,
            "time_impact": f"{recommendation.time_impact:+d} min" if recommendation.time_impact != 0 else "No delay"
        }
    
    @staticmethod
    def format_for_email(recommendation: OptimizationRecommendation) -> str:
        """Format recommendation as email text"""
        email_template = f"""
FUEL OPTIMIZATION RECOMMENDATION
{'=' * 50}

Flight: {recommendation.flight_id}
Priority: {recommendation.priority.upper()}
Generated: {recommendation.generated_at.strftime('%Y-%m-%d %H:%M UTC')}

RECOMMENDATION
--------------
Type: {recommendation.recommendation_type.value.replace('_', ' ').title()}
Action Required: {recommendation.action_required}

EXPECTED BENEFITS
-----------------
Fuel Savings: {recommendation.expected_fuel_savings:.1f} kg
Cost Savings: ${recommendation.expected_cost_savings:.2f} USD
Time Impact: {recommendation.time_impact:+d} minutes
Confidence: {recommendation.confidence_level * 100:.0f}%

WEATHER CONSIDERATIONS
----------------------
{chr(10).join('- ' + factor for factor in recommendation.weather_considerations) if recommendation.weather_considerations else '- None'}

IMPLEMENTATION STEPS
--------------------
{chr(10).join(recommendation.implementation_steps)}

This is an automated recommendation. Please coordinate with dispatch before implementation.
"""
        return email_template
