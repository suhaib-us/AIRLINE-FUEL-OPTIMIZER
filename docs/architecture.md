# Architecture Overview

This document outlines the system architecture, data flows, and component interactions for the Airline Fuel Optimizer.

## System Architecture Diagram

```mermaid
graph TB
    %% Layer Definition
    subgraph "Data Sources"
        A[Flight Data CSV/API]
        B[Weather API METAR/TAF]
        C[Aircraft Performance DB]
    end
    
    subgraph "AWS Lambda / Compute"
        D[Data Ingestion Layer]
        E[Weather Service]
        F[Optimization Engine]
        G[Recommendation Generator]
    end
    
    subgraph "AWS Strands (Step Functions)"
        H1[State 1: Data Ingestion]
        H2[State 2: Weather Analysis]
        H3[State 3: Optimization Compute]
        H4[State 4: Recommendation Gen]
        H5[State 5: Results Publication]
    end
    
    subgraph "MCP Integration Layer"
        I[MCP Message Formatter]
        J[SQS Queue]
        K[SNS Topic]
    end
    
    subgraph "Operations Systems"
        L[Operations Dashboard]
        M[Email/SMS Alerts]
        N[Flight Dispatch System]
    end
    
    %% Connections
    A --> D
    B --> E
    C --> F
    
    D --> H1
    H1 --> H2
    H2 --> E
    E --> H3
    H3 --> F
    F --> H4
    H4 --> G
    G --> H5
    H5 --> I
    
    I --> J
    I --> K
    
    J --> L
    K --> M
    J --> N
    
    %% Styling
    style H1 fill:#ff9999,stroke:#333
    style H2 fill:#ffcc99,stroke:#333
    style H3 fill:#ffff99,stroke:#333
    style H4 fill:#99ff99,stroke:#333
    style H5 fill:#99ccff,stroke:#333
    
    style I fill:#cc99ff,stroke:#333
    style J fill:#ff99cc,stroke:#333
    style K fill:#ff99cc,stroke:#333