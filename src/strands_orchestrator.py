"""
AWS Strands Orchestration - Stateful workflow management
This module manages the multi-step optimization workflow using AWS Step Functions
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """Workflow states for the optimization pipeline"""
    INITIALIZED = "initialized"
    DATA_INGESTION = "data_ingestion"
    WEATHER_ANALYSIS = "weather_analysis"
    OPTIMIZATION_COMPUTE = "optimization_compute"
    RECOMMENDATION_GENERATION = "recommendation_generation"
    RESULTS_PUBLICATION = "results_publication"
    COMPLETED = "completed"
    FAILED = "failed"


class StrandsOrchestrator:
    """
    Orchestrates the stateful ML workflow for fuel optimization
    Uses AWS Step Functions pattern for workflow management
    """
    
    def __init__(self):
        """Initialize the orchestrator"""
        self.workflow_history = []
        
    def create_workflow_definition(self) -> Dict[str, Any]:
        """
        Create AWS Step Functions state machine definition
        
        Returns:
            Step Functions state machine definition in ASL format
        """
        return {
            "Comment": "Airline Fuel Optimization Workflow",
            "StartAt": "DataIngestion",
            "States": {
                "DataIngestion": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:FuelOptimizer-DataIngestion",
                    "Next": "WeatherAnalysis",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "FailureHandler"
                        }
                    ]
                },
                "WeatherAnalysis": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:FuelOptimizer-WeatherAnalysis",
                    "Next": "OptimizationCompute",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ]
                },
                "OptimizationCompute": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:FuelOptimizer-Compute",
                    "Next": "RecommendationGeneration",
                    "TimeoutSeconds": 300
                },
                "RecommendationGeneration": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:FuelOptimizer-Recommendations",
                    "Next": "ResultsPublication"
                },
                "ResultsPublication": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:FuelOptimizer-Publish",
                    "Next": "Success"
                },
                "Success": {
                    "Type": "Succeed"
                },
                "FailureHandler": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:FuelOptimizer-FailureHandler",
                    "Next": "Fail"
                },
                "Fail": {
                    "Type": "Fail",
                    "Error": "WorkflowFailed",
                    "Cause": "Optimization workflow failed"
                }
            }
        }
    
    def execute_workflow_step(
        self,
        state: WorkflowState,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step
        
        Args:
            state: Current workflow state
            input_data: Input data for this step
            
        Returns:
            Output data from the step
        """
        logger.info(f"Executing workflow step: {state}")
        
        step_start = datetime.utcnow()
        
        try:
            # Record state transition
            self.workflow_history.append({
                "state": state,
                "timestamp": step_start.isoformat(),
                "status": "started"
            })
            
            # Execute step logic based on state
            if state == WorkflowState.DATA_INGESTION:
                output = self._step_data_ingestion(input_data)
            elif state == WorkflowState.WEATHER_ANALYSIS:
                output = self._step_weather_analysis(input_data)
            elif state == WorkflowState.OPTIMIZATION_COMPUTE:
                output = self._step_optimization_compute(input_data)
            elif state == WorkflowState.RECOMMENDATION_GENERATION:
                output = self._step_recommendation_generation(input_data)
            elif state == WorkflowState.RESULTS_PUBLICATION:
                output = self._step_results_publication(input_data)
            else:
                raise ValueError(f"Unknown workflow state: {state}")
            
            # Record success
            self.workflow_history.append({
                "state": state,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed",
                "duration_seconds": (datetime.utcnow() - step_start).total_seconds()
            })
            
            return output
            
        except Exception as e:
            logger.error(f"Error in workflow step {state}: {e}")
            self.workflow_history.append({
                "state": state,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            raise
    
    def _step_data_ingestion(self, input_data: Dict) -> Dict:
        """Data ingestion step"""
        logger.info("Step 1: Data Ingestion")
        return {
            "step": "data_ingestion",
            "flight_data": input_data.get("flight_plan"),
            "validation_passed": True,
            "next_state": WorkflowState.WEATHER_ANALYSIS
        }
    
    def _step_weather_analysis(self, input_data: Dict) -> Dict:
        """Weather analysis step"""
        logger.info("Step 2: Weather Analysis")
        return {
            "step": "weather_analysis",
            "weather_data": input_data.get("weather_data", []),
            "analysis_complete": True,
            "next_state": WorkflowState.OPTIMIZATION_COMPUTE
        }
    
    def _step_optimization_compute(self, input_data: Dict) -> Dict:
        """Optimization computation step"""
        logger.info("Step 3: Optimization Compute")
        return {
            "step": "optimization_compute",
            "optimization_result": input_data.get("optimization_result"),
            "computation_complete": True,
            "next_state": WorkflowState.RECOMMENDATION_GENERATION
        }
    
    def _step_recommendation_generation(self, input_data: Dict) -> Dict:
        """Recommendation generation step"""
        logger.info("Step 4: Recommendation Generation")
        return {
            "step": "recommendation_generation",
            "recommendations": input_data.get("recommendations"),
            "generation_complete": True,
            "next_state": WorkflowState.RESULTS_PUBLICATION
        }
    
    def _step_results_publication(self, input_data: Dict) -> Dict:
        """Results publication step"""
        logger.info("Step 5: Results Publication")
        return {
            "step": "results_publication",
            "published": True,
            "publication_timestamp": datetime.utcnow().isoformat(),
            "next_state": WorkflowState.COMPLETED
        }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get current workflow status
        
        Returns:
            Workflow status information
        """
        if not self.workflow_history:
            return {"status": "not_started", "history": []}
        
        last_step = self.workflow_history[-1]
        completed_steps = [h for h in self.workflow_history if h.get("status") == "completed"]
        
        return {
            "status": last_step.get("status"),
            "current_state": last_step.get("state"),
            "completed_steps": len(completed_steps),
            "total_steps": 5,
            "history": self.workflow_history
        }
    
    def reset_workflow(self):
        """Reset workflow state"""
        self.workflow_history = []
        logger.info("Workflow reset")
