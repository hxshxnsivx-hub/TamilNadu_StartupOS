# Tamil Nadu StartupOS - File Structure

## Specification Documents

```
TamilNaduStartupOS/
├── PROJECT_SUMMARY.md              # Executive overview and key highlights
├── FILE_STRUCTURE.md               # This file - navigation guide
│
├── .kiro/
│   └── specs/
│       └── tamil-nadu-startupos/
│           ├── requirements.md     # Comprehensive requirements (577 lines)
│           ├── design.md          # Technical design document (950+ lines)
│           └── tasks.md           # Implementation tasks (600+ lines)
│
└── (Implementation folders to be created during development)
```

## Document Navigation Guide

### 1. Start Here: PROJECT_SUMMARY.md

**Purpose**: Executive overview, high-level architecture, key algorithms

**Read this first** to understand:
- Project vision and value propositions
- Four core categories at a glance
- High-level architecture diagram
- Key algorithms and formulations
- Implementation timeline and team requirements
- KPIs and success metrics

**Length**: ~500 lines  
**Reading Time**: 15-20 minutes

---

### 2. Business Requirements: requirements.md

**Location**: `.kiro/specs/tamil-nadu-startupos/requirements.md`

**Purpose**: Detailed functional requirements with user stories and acceptance criteria

**Sections**:
- Introduction and Glossary
- **CATEGORY 1: IDEATION & ROADMAP** (Requirements 1.1-1.5)
  - Founder profile creation
  - Startup idea validation
  - Roadmap generation
  - Scheme annotation
  - Multilingual voice interaction
  
- **CATEGORY 2: REGISTERED STARTUP JOURNEY** (Requirements 2.1-2.6)
  - Legal entity validation
  - Document upload and OCR
  - Scheme database management
  - CP-SAT eligibility engine
  - Scheme recommendations and ranking
  - Application tracking
  
- **CATEGORY 3: B2B COLLABORATION HUB** (Requirements 3.1-3.5)
  - B2B profile creation with BOM
  - NetworkX bipartite graph construction
  - Multi-tier B2B matching with CP-SAT
  - Trust score calculation
  - Collaboration lifecycle management
  
- **CATEGORY 4: FUNDING & INVESTOR READINESS** (Requirements 4.1-4.5)
  - Funding readiness assessment
  - Gap analysis and recommendations
  - Investor database management
  - CP-SAT investor matching
  - Funding pipeline tracking
  
- **MULTI-AGENT ARCHITECTURE REQUIREMENTS** (Requirements 5.1-5.5)
  - LangGraph Central Orchestrator
  - Specialized agent swarms
  - CP-SAT Boundary Engine
  - NetworkX Graph Engine
  - Multilingual embedding and translation services
  
- **DATA MODEL AND STORAGE REQUIREMENTS** (Requirements 6.1-6.2)
  - Founder and startup profile data models
  - Scheme database schema
  - (Additional sections may be present)

**Length**: 577 lines  
**Reading Time**: 45-60 minutes  
**Use For**: Understanding business requirements, writing acceptance tests

---

### 3. Technical Design: design.md

**Location**: `.kiro/specs/tamil-nadu-startupos/design.md`

**Purpose**: Detailed technical architecture, algorithms, data models, APIs

**Sections**:
- **Overview**: System purpose, capabilities, differentiators
- **Architecture**: High-level system architecture, multi-agent architecture
  - Central Orchestrator Design (LangGraph state machine)
  - Specialized Agent Swarms (Profile, Scheme, B2B, Roadmap, Funding)
  - Swarm communication patterns
  
- **Components and Interfaces**:
  - CPSAT_Boundary - Constraint Programming Engine
    - Scheme eligibility constraint model
    - B2B matching constraint model
    - Investor matching constraint model
  - Graph_Engine - NetworkX Bipartite Matching
    - Edge weight computation algorithm
    - Maximum weight matching algorithm
  - Embedding_Service - Multilingual Semantic Understanding
  - Translation_Service - Multilingual Content Translation
  
- **Data Models**: Complete data models with PostgreSQL schemas
  - Founder Profile, Startup Profile, Scheme, B2B Profile, Investor
  - Graph storage, embeddings storage (pgvector)
  
- **API Design**: REST API structure and key endpoints
  - Scheme eligibility check endpoint (detailed implementation)
  - B2B match request endpoint (detailed implementation)
  - Funding readiness assessment endpoint (detailed implementation)
  
- **Error Handling**: Error classification, response format, exception handling in swarms, retry logic, circuit breaker pattern
  
- **Correctness Properties**: Mathematical guarantees for CP-SAT, data integrity invariants, idempotency guarantees, transactional guarantees
  
- **Testing Strategy**: Unit testing, integration testing, property-based testing, performance testing, security testing

**Length**: 950+ lines  
**Reading Time**: 60-90 minutes  
**Use For**: Implementation reference, architectural decisions, API contracts

---

### 4. Implementation Plan: tasks.md

**Location**: `.kiro/specs/tamil-nadu-startupos/tasks.md`

**Purpose**: Granular, actionable tasks organized by implementation phases

**Sections**:
- **Task Organization**: Overview of phases, effort estimation, priority levels
  
- **PHASE 1: FOUNDATION & IDEATION** (Tasks 1.1-1.9)
  - Project setup and infrastructure
  - Database schema - founders and profiles
  - Profile Swarm implementation
  - Document verification service with OCR
  - Translation service (IndicTrans2)
  - Embedding service (IndicBERT)
  - Roadmap Swarm implementation
  - Central Orchestrator - LangGraph state machine
  - FastAPI endpoints - profile and ideation
  
- **PHASE 2: REGISTERED STARTUP & SCHEMES** (Tasks 2.1-2.7)
  - Legal validation service (MCA21, DPIIT, GST)
  - Scheme database schema
  - CP-SAT Boundary Engine - scheme eligibility
  - Scheme Swarm implementation
  - Scheme annotation on roadmap milestones
  - FastAPI endpoints - schemes
  - Multilingual UI expansion (Hindi)
  
- **PHASE 3: B2B COLLABORATION ENGINE** (Tasks 3.1-3.6)
  - B2B profile database schema
  - NetworkX Graph Engine implementation
  - CP-SAT B2B matching with capacity constraints
  - B2B Swarm implementation
  - B2B collaboration lifecycle management
  - FastAPI endpoints - B2B collaboration
  
- **PHASE 4: FUNDING NAVIGATOR & INVESTOR READINESS** (Tasks 4.1-4.7)
  - Investor database schema
  - Funding readiness assessment engine
  - Gap analysis and recommendation engine
  - CP-SAT investor matching
  - Funding Swarm implementation
  - Funding pipeline management
  - FastAPI endpoints - funding and investors
  
- **PHASE 5: OPTIMIZATION & LEARNING** (Tasks 5.1-5.7)
  - Graph Neural Network for B2B matching
  - Analytics and impact dashboard
  - Continuous agent evaluation
  - Security hardening and penetration testing
  - Performance testing and optimization
  - Deployment and infrastructure
  - Documentation and user guides
  
- **Summary**: Total tasks (180+), critical path, timeline estimates (22-32 weeks), team size recommendations, technology stack

**Length**: 600+ lines  
**Reading Time**: 45-60 minutes  
**Use For**: Sprint planning, task assignment, progress tracking

---

## How to Use These Documents

### For Project Managers:
1. Read **PROJECT_SUMMARY.md** for executive overview
2. Review **tasks.md** for timeline and resource planning
3. Use **requirements.md** for stakeholder alignment

### For Architects:
1. Read **PROJECT_SUMMARY.md** for high-level architecture
2. Deep dive into **design.md** for technical details
3. Reference **requirements.md** for functional constraints

### For Developers:
1. Start with **PROJECT_SUMMARY.md** to understand the system
2. Refer to **design.md** for implementation details
3. Follow **tasks.md** for step-by-step implementation
4. Check **requirements.md** for acceptance criteria

### For QA Engineers:
1. Read **requirements.md** for acceptance criteria
2. Review **design.md** testing strategy section
3. Use **tasks.md** to identify what to test in each phase

### For Product Managers:
1. Read **PROJECT_SUMMARY.md** for product vision
2. Deep dive into **requirements.md** for user stories
3. Use **tasks.md** for release planning

---

## Quick Reference: Key Sections

### Algorithms and Formulations
- **Location**: PROJECT_SUMMARY.md, Section "Key Algorithms and Formulations"
- **Also in**: design.md, Components section for detailed implementations

### Data Models
- **Location**: design.md, Section "Data Models"
- **Includes**: All entity schemas with PostgreSQL DDL

### API Endpoints
- **Location**: design.md, Section "API Design"
- **Includes**: Request/response examples, implementation code

### Multi-Agent Architecture
- **Location**: design.md, Section "Architecture" → "Multi-Agent Architecture"
- **Includes**: LangGraph state machines, swarm communication patterns

### Constraint Programming Models
- **Location**: design.md, Section "Components" → "CPSAT_Boundary"
- **Includes**: Decision variables, constraints, objectives for all 3 use cases

### Task Dependencies
- **Location**: tasks.md, each task section lists dependencies
- **Use for**: Understanding what must be completed before starting a task

---

## Document Versions

| Document | Version | Lines | Last Updated |
|----------|---------|-------|--------------|
| PROJECT_SUMMARY.md | 1.0 | 500 | 2024 |
| requirements.md | 1.0 | 577 | 2024 |
| design.md | 1.0 | 950+ | 2024 |
| tasks.md | 1.0 | 600+ | 2024 |

**Total Specification**: 2,600+ lines of comprehensive documentation

---

## Contributing to Documentation

When updating specifications:

1. **Update version number** in document header
2. **Add changelog entry** at end of document
3. **Cross-reference** updates across all 3 documents
4. **Update PROJECT_SUMMARY.md** if high-level changes occur
5. **Maintain consistency** in terminology (use Glossary from requirements.md)

---

## Additional Resources

### External Documentation (To Be Created)
- API Documentation (Swagger/OpenAPI) - Auto-generated from FastAPI
- User Guides - One per category (4 guides)
- Developer Setup Guide - Local environment setup
- Deployment Guide - Kubernetes deployment procedures
- Troubleshooting Guide - Common issues and solutions

### Code Repository Structure (Recommended)
```
tamil-nadu-startupos/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph agent swarms
│   │   ├── services/        # CP-SAT, Graph, Embedding, Translation
│   │   ├── models/          # Pydantic data models
│   │   ├── routers/         # FastAPI endpoints
│   │   └── db/              # Database models, migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── property/        # Hypothesis property-based tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── i18n/            # Multilingual translations
│   └── package.json
├── infrastructure/
│   ├── docker/
│   ├── kubernetes/
│   └── terraform/
├── docs/
│   ├── api/
│   ├── user-guides/
│   └── architecture/
└── .github/
    └── workflows/           # CI/CD pipelines
```

---

**This file structure provides a complete navigation guide to the Tamil Nadu StartupOS specification. All documents are ready for implementation.**
