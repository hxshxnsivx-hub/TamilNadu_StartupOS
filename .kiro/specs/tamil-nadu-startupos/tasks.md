# Tasks: Tamil Nadu StartupOS (Vanigam)

## Overview

This document provides a comprehensive, phase-by-phase breakdown of implementation tasks for Tamil Nadu StartupOS (Vanigam). Tasks are organized into 5 major phases aligned with the project blueprint, with clear dependencies, acceptance criteria, and effort estimates.

## Task Organization

- **Phases**: 5 major phases (Foundation, Registered Startup, B2B, Funding, Optimization)
- **Subtasks**: Each phase broken into implementation units
- **Dependencies**: Explicit task dependencies marked
- **Effort**: T-shirt sizing (XS: <4h, S: 4-8h, M: 1-2d, L: 3-5d, XL: 1-2w)
- **Priority**: P0 (Critical), P1 (High), P2 (Medium), P3 (Low)

---

## PHASE 1: FOUNDATION & IDEATION (Category 1)

### Task 1.1: Project Setup and Infrastructure

**Description**: Set up project structure, dependencies, and development environment

**Subtasks**:
- [ ] 1.1.1: Initialize Python project with Poetry/pip requirements
  - FastAPI, LangGraph, OR-Tools, NetworkX, Transformers (IndicBERT), PostgreSQL drivers, Redis client
  - Effort: S, Priority: P0
- [ ] 1.1.2: Set up PostgreSQL database with pgvector extension
  - Install PostgreSQL 15+, enable pgvector, create development database
  - Effort: S, Priority: P0
- [ ] 1.1.3: Set up Redis for caching
  - Install Redis, configure persistence, set up connection pooling
  - Effort: XS, Priority: P0
- [ ] 1.1.4: Configure S3-compatible storage (MinIO/AWS S3) for documents
  - Set up buckets, configure access policies, test upload/download
  - Effort: S, Priority: P0
- [ ] 1.1.5: Set up logging and monitoring infrastructure
  - Configure structured logging (JSON), set up log aggregation
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- All dependencies installed and importable
- Database connects successfully with pgvector enabled
- Redis cache operational with test key-value operations
- S3 storage accessible with test file upload
- Logs written to files and stdout in JSON format

**Dependencies**: None

---

### Task 1.2: Database Schema - Founders and Profiles

**Description**: Implement founder profile database schema with completeness scoring

**Subtasks**:
- [ ] 1.2.1: Create founders table with all fields
  - Schema from design.md, include soft delete, constraints
  - Effort: S, Priority: P0

- [ ] 1.2.2: Create startups table with foreign key to founders
  - Schema from design.md, include verification status fields
  - Effort: S, Priority: P0
- [ ] 1.2.3: Create documents table for file uploads and verification
  - document_type enum, extracted_data JSONB, verification_status
  - Effort: S, Priority: P0
- [ ] 1.2.4: Create profile_completeness tracking table
  - Track missing_fields, verified_fields, completeness_score
  - Effort: XS, Priority: P0
- [ ] 1.2.5: Write database migration scripts
  - Use Alembic for versioned migrations, create initial migration
  - Effort: S, Priority: P0
- [ ] 1.2.6: Create database indexes for performance
  - Index email, phone, location, domain, stage fields
  - Effort: XS, Priority: P1

**Acceptance Criteria**:
- All tables created with correct schema
- Foreign key constraints enforced
- Check constraints validate data (email format, phone format, positive values)
- Indexes created on frequently-queried fields
- Migration scripts run successfully up and down

**Dependencies**: Task 1.1 (database setup)

---

### Task 1.3: Profile Swarm - Data Collection and Completeness Scoring

**Description**: Implement Profile Swarm (Swarm 1) for founder profile management

**Subtasks**:
- [ ] 1.3.1: Implement FounderProfile and StartupProfile data models (Pydantic)
  - Include all fields from design.md, validation rules
  - Effort: M, Priority: P0
- [ ] 1.3.2: Implement CompletenessScorer agent
  - Calculate 40/60/80/100% score based on field presence and verification
  - Effort: M, Priority: P0
- [ ] 1.3.3: Implement DataCollector agent
  - Prompt for missing fields, handle multilingual input
  - Effort: M, Priority: P0
- [ ] 1.3.4: Implement ProfileSupervisor agent (LangGraph)
  - Coordinate data collection, verification, scoring
  - Effort: L, Priority: P0
- [ ] 1.3.5: Write unit tests for completeness scoring logic
  - Test all score thresholds (40, 60, 80, 100)
  - Effort: S, Priority: P0

**Acceptance Criteria**:
- Founder profile can be created with basic fields (40% score)
- Completeness score updates correctly as fields are added
- Missing fields list is accurate
- Profile Swarm coordinates sub-agents correctly
- Unit tests achieve 80%+ coverage

**Dependencies**: Task 1.2 (database schema)

---

### Task 1.4: Document Verification Service with OCR

**Description**: Implement document upload, OCR extraction, and verification

**Subtasks**:
- [ ] 1.4.1: Implement S3 upload/download service
  - Upload documents, generate signed URLs, delete files
  - Effort: M, Priority: P0
- [ ] 1.4.2: Integrate OCR service (Tesseract or cloud OCR)
  - Extract text from PDF/JPG/PNG, return confidence scores
  - Effort: L, Priority: P0
- [ ] 1.4.3: Implement DocumentProcessor agent
  - Parse extracted text, identify document type, extract key fields
  - Effort: L, Priority: P0
- [ ] 1.4.4: Implement document validation logic
  - Check digital signatures, QR codes, cross-reference with APIs where available
  - Effort: M, Priority: P1
- [ ] 1.4.5: Implement fallback for low-confidence OCR
  - Flag for manual review, use alternative OCR service
  - Effort: M, Priority: P1
- [ ] 1.4.6: Write integration tests for document processing
  - Test with sample Aadhaar, PAN, mark sheets
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Documents uploaded to S3 successfully
- OCR extracts text with confidence scores
- Document type identified correctly (Aadhaar, PAN, etc.)
- Key fields extracted (name, DOB, ID numbers)
- Low-confidence documents flagged for review
- Integration tests pass with sample documents

**Dependencies**: Task 1.1.4 (S3 setup), Task 1.3 (Profile Swarm)

---

### Task 1.5: Translation Service (IndicTrans2)

**Description**: Implement multilingual translation service for Tamil and Hindi

**Subtasks**:
- [ ] 1.5.1: Download and load IndicTrans2 model
  - Set up model loading, configure device (CPU/GPU)
  - Effort: M, Priority: P0
- [ ] 1.5.2: Implement TranslationService class
  - translate() method for en<->ta, en<->hi, ta<->hi
  - Effort: M, Priority: P0
- [ ] 1.5.3: Create domain glossary for startup terminology
  - Define mappings for funding, scheme, roadmap, B2B, etc.
  - Effort: S, Priority: P0
- [ ] 1.5.4: Implement glossary-aware translation
  - Replace terms with placeholders, translate, restore
  - Effort: M, Priority: P0
- [ ] 1.5.5: Implement translation caching in Redis
  - Cache by (text_hash, source_lang, target_lang)
  - Effort: S, Priority: P1
- [ ] 1.5.6: Write unit tests for translation accuracy
  - Test BLEU scores, glossary preservation
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Translation works for all language pairs (en-ta, en-hi, ta-hi)
- Domain-specific terms preserved correctly
- Translation cached in Redis with 7-day TTL
- BLEU score >= 40 for general text, >= 35 for domain text
- Unit tests verify translation quality

**Dependencies**: Task 1.1 (Redis setup)

---

### Task 1.6: Embedding Service (IndicBERT)

**Description**: Implement semantic embedding service using IndicBERT

**Subtasks**:
- [ ] 1.6.1: Download and load IndicBERT model
  - ai4bharat/indic-bert, configure tokenizer
  - Effort: M, Priority: P0
- [ ] 1.6.2: Implement EmbeddingService class
  - embed() for single text, embed_batch() for multiple
  - Effort: M, Priority: P0
- [ ] 1.6.3: Implement cosine similarity calculation
  - Numpy-based dot product and normalization
  - Effort: XS, Priority: P0
- [ ] 1.6.4: Implement embedding caching in Redis
  - Cache by (text_hash, language) for 7 days
  - Effort: S, Priority: P1
- [ ] 1.6.5: Create scheme_embeddings and startup_domain_embeddings tables
  - Tables with vector(768) columns, pgvector indexes
  - Effort: S, Priority: P0
- [ ] 1.6.6: Write unit tests for embedding generation and similarity
  - Test embedding dimensions, similarity ranges
  - Effort: S, Priority: P1

**Acceptance Criteria**:
- Embeddings generated with shape (768,)
- Cosine similarity returns values in [-1, 1]
- Embeddings cached in Redis
- pgvector tables created with IVFFlat indexes
- Similar texts have high similarity (>0.7)
- Unit tests verify embedding quality

**Dependencies**: Task 1.1 (Redis, PostgreSQL with pgvector)

---

### Task 1.7: Roadmap Swarm - Idea Validation and Roadmap Generation

**Description**: Implement Roadmap Swarm (Swarm 4) for startup idea processing

**Subtasks**:
- [ ] 1.7.1: Implement IdeaExtractor agent
  - Extract problem, solution, market, value proposition from natural language
  - Effort: L, Priority: P0
- [ ] 1.7.2: Implement FeasibilityAnalyzer agent
  - Assess market size, competition, technical complexity, regulatory barriers
  - Effort: L, Priority: P0
- [ ] 1.7.3: Implement MilestoneGenerator agent
  - Generate 5-15 milestones across phases (Ideation, Validation, MVP, Launch, Growth, Scale)
  - Effort: L, Priority: P0
- [ ] 1.7.4: Implement milestone dependency resolution
  - Topological sort of milestones, identify critical path
  - Effort: M, Priority: P0
- [ ] 1.7.5: Implement RoadmapSupervisor agent (LangGraph)
  - Orchestrate idea extraction → feasibility → milestone generation
  - Effort: L, Priority: P0
- [ ] 1.7.6: Create roadmaps and milestones database tables
  - Store roadmap with milestones, dependencies, timelines
  - Effort: M, Priority: P0
- [ ] 1.7.7: Write unit tests for roadmap generation
  - Test milestone sequencing, dependency resolution
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Startup idea parsed into structured concept elements
- Feasibility score (0-100) generated
- Roadmap with 5-15 milestones created
- Milestones sequenced with dependencies
- Critical path identified
- Roadmap stored in database
- Unit tests verify milestone logic

**Dependencies**: Task 1.5 (Translation Service)

---

### Task 1.8: Central Orchestrator - LangGraph State Machine

**Description**: Implement Central Orchestrator for conversation management

**Subtasks**:
- [ ] 1.8.1: Define ConversationState TypedDict
  - user_id, session_id, messages, current_intent, extracted_entities, active_swarm
  - Effort: S, Priority: P0
- [ ] 1.8.2: Implement intent classification node
  - Classify into: Profile Update, Idea Input, Roadmap Request, Scheme Query, B2B Search, Funding Query
  - Effort: M, Priority: P0
- [ ] 1.8.3: Implement LangGraph state machine with nodes
  - greeting, intent_recognition, profile_collection, idea_discussion, clarification, error_handling
  - Effort: L, Priority: P0
- [ ] 1.8.4: Implement conditional edges for intent routing
  - Route to appropriate swarm based on classified intent
  - Effort: M, Priority: P0
- [ ] 1.8.5: Implement conversation context stack
  - Support context switching, pause/resume tasks
  - Effort: M, Priority: P1
- [ ] 1.8.6: Implement timeout handling
  - Save context after 30 minutes of inactivity
  - Effort: S, Priority: P1
- [ ] 1.8.7: Write integration tests for conversation flow
  - Test multi-turn conversations, context switching
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Intent classified correctly with >80% accuracy
- Conversations route to correct swarm
- Multi-turn conversations maintain context
- Context switching works (pause one task, start another, return)
- Timeouts handled gracefully
- Integration tests verify conversation flow

**Dependencies**: Task 1.3 (Profile Swarm), Task 1.7 (Roadmap Swarm)

---

### Task 1.9: FastAPI Endpoints - Profile and Ideation

**Description**: Implement REST API endpoints for Profile and Ideation categories

**Subtasks**:
- [ ] 1.9.1: Implement /auth endpoints (register, login, refresh)
  - JWT authentication with refresh tokens, password hashing (bcrypt)
  - Effort: M, Priority: P0
- [ ] 1.9.2: Implement /profiles endpoints
  - GET /profiles/{id}, PUT /profiles/{id}, POST /profiles/{id}/documents
  - Effort: M, Priority: P0
- [ ] 1.9.3: Implement /startups endpoints
  - POST /startups, GET /startups/{id}, PUT /startups/{id}
  - Effort: M, Priority: P0
- [ ] 1.9.4: Implement /ideation endpoints
  - POST /ideation/ideas, GET /ideation/ideas/{id}, POST /ideation/ideas/{id}/roadmap
  - Effort: M, Priority: P0
- [ ] 1.9.5: Implement request validation with Pydantic models
  - Validate all inputs, return 422 for validation failures
  - Effort: M, Priority: P0
- [ ] 1.9.6: Implement error handling middleware
  - Standardized ErrorResponse format from design.md
  - Effort: M, Priority: P0
- [ ] 1.9.7: Implement rate limiting middleware
  - 100 requests/minute per user, 1000/minute globally
  - Effort: S, Priority: P1
- [ ] 1.9.8: Write API integration tests
  - Test all endpoints with various inputs, edge cases
  - Effort: L, Priority: P1

**Acceptance Criteria**:
- All endpoints return correct status codes and responses
- Authentication required for protected endpoints
- Input validation works correctly
- Error responses follow standardized format
- Rate limiting enforced
- API integration tests achieve 80%+ coverage

**Dependencies**: Task 1.3 (Profile Swarm), Task 1.7 (Roadmap Swarm), Task 1.8 (Central Orchestrator)

---

## PHASE 2: REGISTERED STARTUP & SCHEMES (Category 2)

### Task 2.1: Legal Validation Service

**Description**: Implement legal entity validation through MCA21, DPIIT, GST registries

**Subtasks**:
- [ ] 2.1.1: Implement MCA21 CIN validation
  - API integration or scraping, extract company details
  - Effort: L, Priority: P0
- [ ] 2.1.2: Implement DPIIT recognition number validation
  - Query Startup India portal, verify recognition status
  - Effort: L, Priority: P0
- [ ] 2.1.3: Implement GSTIN validation
  - Query GST portal, validate registration and filing status
  - Effort: M, Priority: P0
- [ ] 2.1.4: Implement LegalValidator class
  - Coordinate validations, update verification_status in database
  - Effort: M, Priority: P0
- [ ] 2.1.5: Implement retry logic with exponential backoff
  - Handle API timeouts and failures gracefully
  - Effort: S, Priority: P1
- [ ] 2.1.6: Implement circuit breaker pattern
  - Prevent cascading failures from external service outages
  - Effort: M, Priority: P1
- [ ] 2.1.7: Write integration tests for legal validation
  - Test with valid and invalid CINs, DPIIT numbers, GSTINs
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- CIN validation returns company name, incorporation date, entity type
- DPIIT validation returns recognition status and date
- GSTIN validation returns registration status
- verification_status updated to "verified" or "rejected"
- Retry logic handles transient failures
- Circuit breaker opens after 5 consecutive failures
- Integration tests verify validation logic

**Dependencies**: Task 1.2 (database schema)

---

### Task 2.2: Scheme Database Schema and Management

**Description**: Implement comprehensive scheme database with eligibility criteria

**Subtasks**:
- [ ] 2.2.1: Create schemes table
  - Schema from design.md, include eligibility_criteria JSONB
  - Effort: M, Priority: P0
- [ ] 2.2.2: Create scheme_benefits table
  - Store benefits like interest rate, subsidy percentage
  - Effort: S, Priority: P0
- [ ] 2.2.3: Create scheme_applications table
  - Track application status, decision dates, funding amounts
  - Effort: S, Priority: P0
- [ ] 2.2.4: Implement scheme versioning
  - Preserve historical eligibility criteria when schemes update
  - Effort: M, Priority: P1
- [ ] 2.2.5: Create database migration for scheme tables
  - Alembic migration with indexes on scheme_type, status, deadline
  - Effort: S, Priority: P0
- [ ] 2.2.6: Seed database with initial schemes
  - SISFS, Fund of Funds, PMEGP, MUDRA, Stand-Up India, TANSEED
  - Effort: M, Priority: P0
- [ ] 2.2.7: Implement admin API for scheme management
  - POST /admin/schemes, PUT /admin/schemes/{id}, DELETE /admin/schemes/{id}
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Scheme tables created with correct schema
- JSONB eligibility_criteria field supports complex rules
- Scheme versioning preserves historical data
- Initial schemes seeded in database
- Admin API allows CRUD operations on schemes
- Migrations run successfully

**Dependencies**: Task 1.2 (database setup)

---

### Task 2.3: CP-SAT Boundary Engine - Scheme Eligibility

**Description**: Implement constraint programming engine for scheme eligibility

**Subtasks**:
- [ ] 2.3.1: Implement CPSATBoundary class
  - create_model(), add_bool_var(), add_int_var(), add_constraint(), solve()
  - Effort: L, Priority: P0
- [ ] 2.3.2: Implement constraint encoding for demographic rules
  - Age range, gender, location, caste category constraints
  - Effort: M, Priority: P0
- [ ] 2.3.3: Implement constraint encoding for education rules
  - Qualification level, first graduate status
  - Effort: M, Priority: P0
- [ ] 2.3.4: Implement constraint encoding for startup rules
  - Entity type, domain, stage, revenue, employees
  - Effort: M, Priority: P0
- [ ] 2.3.5: Implement constraint encoding for document requirements
  - Required verified documents as boolean constraints
  - Effort: M, Priority: P0
- [ ] 2.3.6: Implement compound constraint support (AND, OR, NOT)
  - Handle eligibility like "First_Graduate AND (SC OR ST OR OBC)"
  - Effort: M, Priority: P0
- [ ] 2.3.7: Implement infeasibility analysis (IIS)
  - Identify minimal conflicting constraints
  - Effort: M, Priority: P1
- [ ] 2.3.8: Write unit tests for CP-SAT constraint logic
  - Test each constraint type, compound rules
  - Effort: L, Priority: P0
- [ ] 2.3.9: Write property-based tests with Hypothesis
  - Verify eligible schemes satisfy all constraints
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- CP-SAT model created and solved successfully
- All constraint types encoded correctly
- Compound constraints work (AND, OR, NOT)
- Infeasible models return violated constraints
- Solver completes within 10 seconds for interactive queries
- Unit tests achieve 90%+ coverage
- Property-based tests verify correctness

**Dependencies**: None (core library implementation)

---


### Task 2.4: Scheme Swarm - Intelligence and Matching

**Description**: Implement Scheme Swarm (Swarm 2) for scheme discovery and ranking

**Subtasks**:
- [ ] 2.4.1: Implement SchemeRetriever agent
  - Query scheme database with filters (type, deadline, funding range)
  - Effort: M, Priority: P0
- [ ] 2.4.2: Implement EligibilityChecker agent
  - Interface with CPSAT_Boundary for constraint solving
  - Effort: M, Priority: P0
- [ ] 2.4.3: Implement Ranker agent
  - Compute relevance score from funding match, stage alignment, domain fit, deadline urgency, success rate
  - Effort: M, Priority: P0
- [ ] 2.4.4: Implement domain fit calculation using embeddings
  - Cosine similarity between startup domain and scheme focus areas
  - Effort: M, Priority: P0
- [ ] 2.4.5: Implement Explainer agent
  - Generate natural language explanations for eligibility/ineligibility
  - Effort: M, Priority: P1
- [ ] 2.4.6: Implement SchemeSupervisor agent (LangGraph)
  - Orchestrate retrieval → eligibility → ranking → explanation
  - Effort: L, Priority: P0
- [ ] 2.4.7: Write unit tests for scheme ranking logic
  - Test relevance score calculation with various inputs
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Scheme retrieval filters by type, deadline, amount
- Eligibility checking uses CP-SAT correctly
- Relevance score computed from 5 weighted components
- Domain fit uses embedding similarity
- Explanations generated for ineligible schemes
- Scheme Swarm coordinates sub-agents correctly
- Unit tests verify ranking logic

**Dependencies**: Task 2.2 (scheme database), Task 2.3 (CP-SAT), Task 1.6 (Embedding Service)

---

### Task 2.5: Scheme Annotation on Roadmap Milestones

**Description**: Annotate roadmap milestones with relevant schemes

**Subtasks**:
- [ ] 2.5.1: Implement SchemeAnnotator agent
  - Analyze each milestone, identify applicable schemes
  - Effort: M, Priority: P0
- [ ] 2.5.2: Integrate SchemeAnnotator with Roadmap Swarm
  - Call Scheme_Swarm for each milestone during roadmap generation
  - Effort: M, Priority: P0
- [ ] 2.5.3: Create milestone_scheme_annotations junction table
  - Link milestones to top 3-5 schemes with relevance scores
  - Effort: S, Priority: P0
- [ ] 2.5.4: Implement scheme re-annotation on profile updates
  - Trigger when completeness_score increases
  - Effort: M, Priority: P1
- [ ] 2.5.5: Write integration tests for scheme annotation
  - Test annotation across various roadmap milestones
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Each milestone annotated with 3-5 relevant schemes
- Annotations stored in database
- Re-annotation triggered on profile completeness increase
- Integration tests verify annotation quality

**Dependencies**: Task 1.7 (Roadmap Swarm), Task 2.4 (Scheme Swarm)

---

### Task 2.6: FastAPI Endpoints - Schemes

**Description**: Implement REST API endpoints for scheme discovery and applications

**Subtasks**:
- [ ] 2.6.1: Implement GET /schemes endpoint
  - List schemes with filters (type, deadline, amount range)
  - Effort: M, Priority: P0
- [ ] 2.6.2: Implement GET /schemes/{id} endpoint
  - Get detailed scheme information
  - Effort: S, Priority: P0
- [ ] 2.6.3: Implement POST /schemes/eligibility endpoint
  - Check eligibility using CP-SAT, return eligible and ineligible schemes
  - Effort: M, Priority: P0
- [ ] 2.6.4: Implement POST /schemes/applications endpoint
  - Create scheme application, track status
  - Effort: M, Priority: P0
- [ ] 2.6.5: Implement GET /schemes/applications endpoint
  - List all applications for a startup with status
  - Effort: S, Priority: P0
- [ ] 2.6.6: Implement reminder notifications for deadlines
  - Send notifications 7 days and 1 day before deadline
  - Effort: M, Priority: P1
- [ ] 2.6.7: Write API integration tests for scheme endpoints
  - Test eligibility checking, application tracking
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- All scheme endpoints return correct responses
- Eligibility checking works with CP-SAT integration
- Applications tracked with status transitions
- Deadline reminders sent automatically
- API integration tests achieve 80%+ coverage

**Dependencies**: Task 2.4 (Scheme Swarm), Task 2.3 (CP-SAT)

---

### Task 2.7: Multilingual UI Expansion (Hindi)

**Description**: Extend UI and content to Hindi language

**Subtasks**:
- [ ] 2.7.1: Create i18n locale files for Hindi
  - Translate UI strings, button labels, messages
  - Effort: M, Priority: P1
- [ ] 2.7.2: Implement dynamic scheme description translation
  - Translate scheme names, descriptions using Translation_Service
  - Effort: M, Priority: P1
- [ ] 2.7.3: Implement voice input support (Whisper for Hindi)
  - Transcribe Hindi speech to text
  - Effort: L, Priority: P2
- [ ] 2.7.4: Implement voice output support (TTS for Hindi)
  - Text-to-speech for Hindi responses
  - Effort: M, Priority: P2
- [ ] 2.7.5: Create simplified UX for low-literacy users
  - Larger fonts, icon-first design, voice prompts
  - Effort: L, Priority: P2

**Acceptance Criteria**:
- UI displays in Hindi when language preference is set
- Scheme descriptions translated dynamically
- Voice input transcribes Hindi accurately
- Voice output speaks Hindi responses
- Simplified UX improves accessibility

**Dependencies**: Task 1.5 (Translation Service)

---

## PHASE 3: B2B COLLABORATION ENGINE (Category 3)

### Task 3.1: B2B Profile Database Schema

**Description**: Implement B2B profile schema for all 4 tiers

**Subtasks**:
- [ ] 3.1.1: Create b2b_profiles table
  - Schema from design.md, support all 4 tiers (T1-T4)
  - Effort: M, Priority: P0
- [ ] 3.1.2: Create b2b_collaborations table
  - Track collaboration lifecycle, status, metrics
  - Effort: M, Priority: P0
- [ ] 3.1.3: Create collaboration_feedback table
  - Store feedback across 5 dimensions (delivery, quality, communication, pricing, satisfaction)
  - Effort: S, Priority: P0
- [ ] 3.1.4: Create trust_scores table
  - Calculate and store trust scores (0-100) with history
  - Effort: S, Priority: P0
- [ ] 3.1.5: Create database migration for B2B tables
  - Alembic migration with indexes
  - Effort: S, Priority: P0

**Acceptance Criteria**:
- B2B profile tables created with support for all tiers
- Collaboration lifecycle tracked in database
- Feedback and trust scores stored correctly
- Migrations run successfully

**Dependencies**: Task 1.2 (database setup)

---

### Task 3.2: NetworkX Graph Engine - Bipartite Graph Construction

**Description**: Implement graph-based B2B matching engine

**Subtasks**:
- [ ] 3.2.1: Create b2b_graph_nodes and b2b_graph_edges tables
  - Store bipartite graph in PostgreSQL
  - Effort: M, Priority: P0
- [ ] 3.2.2: Implement GraphEngine class
  - add_demand_node(), add_supply_node(), add_edge(), update_edge_weight()
  - Effort: M, Priority: P0
- [ ] 3.2.3: Implement edge weight computation algorithm
  - Calculate from spec similarity, price compatibility, capacity alignment, geographic proximity
  - Effort: M, Priority: P0
- [ ] 3.2.4: Implement specification similarity using embeddings
  - Cosine similarity of IndicBERT embeddings for item descriptions
  - Effort: M, Priority: P0
- [ ] 3.2.5: Implement price compatibility calculation
  - 100 - |buyer_budget - supplier_price| / buyer_budget * 100
  - Effort: S, Priority: P0
- [ ] 3.2.6: Implement capacity alignment check
  - Verify supplier capacity meets buyer quantity requirements
  - Effort: S, Priority: P0
- [ ] 3.2.7: Implement geographic proximity calculation
  - Distance-based scoring with inter-state penalty
  - Effort: M, Priority: P0
- [ ] 3.2.8: Implement maximum weight matching algorithm
  - Use NetworkX bipartite matching
  - Effort: M, Priority: P0
- [ ] 3.2.9: Implement top-k matches per node
  - Sort neighbors by edge weight, return top k
  - Effort: S, Priority: P0
- [ ] 3.2.10: Implement graph persistence and loading
  - Serialize/deserialize graph to/from PostgreSQL
  - Effort: M, Priority: P0
- [ ] 3.2.11: Write unit tests for graph operations
  - Test node addition, edge weight calculation, matching
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Bipartite graph constructed with demand and supply nodes
- Edge weights computed from 4 components (40%, 30%, 20%, 10%)
- Maximum weight matching finds optimal assignments
- Top-k matches returned correctly
- Graph persisted to and loaded from database
- Unit tests verify graph logic

**Dependencies**: Task 1.6 (Embedding Service), Task 3.1 (B2B schema)

---

### Task 3.3: CP-SAT B2B Matching with Capacity Constraints

**Description**: Implement constraint-optimized B2B matching

**Subtasks**:
- [ ] 3.3.1: Extend CPSATBoundary for B2B matching model
  - Decision variables: match[d][s], allocation[d][s]
  - Effort: M, Priority: P0
- [ ] 3.3.2: Implement capacity constraints
  - Upper bound: supplier max capacity not exceeded
  - Lower bound: supplier min order quantity met
  - Effort: M, Priority: P0
- [ ] 3.3.3: Implement demand satisfaction constraints
  - Total allocation meets demand quantity
  - Effort: S, Priority: P0
- [ ] 3.3.4: Implement specification and price constraints
  - Specification similarity >= 0.7, price within budget
  - Effort: M, Priority: P0
- [ ] 3.3.5: Implement soft constraints with penalties
  - Inter-state penalty (50 points), exclusivity preference penalty (100 points)
  - Effort: M, Priority: P0
- [ ] 3.3.6: Implement objective: maximize total match quality
  - Σ match[d][s] * edge_weight[d][s] - penalties
  - Effort: S, Priority: P0
- [ ] 3.3.7: Implement constraint relaxation for infeasible models
  - Iteratively relax soft constraints, report which were relaxed
  - Effort: M, Priority: P1
- [ ] 3.3.8: Write unit tests for B2B CP-SAT logic
  - Test capacity constraints, objective optimization
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- CP-SAT model optimizes B2B matches subject to constraints
- Capacity constraints enforced correctly
- Soft constraints relaxed when needed
- Objective maximizes match quality
- Unit tests verify constraint logic

**Dependencies**: Task 2.3 (CP-SAT Boundary), Task 3.2 (Graph Engine)

---

### Task 3.4: B2B Swarm - Collaboration Matching

**Description**: Implement B2B Swarm (Swarm 3) for collaboration discovery

**Subtasks**:
- [ ] 3.4.1: Implement BOMParser agent
  - Extract structured BOM from natural language descriptions
  - Effort: M, Priority: P0
- [ ] 3.4.2: Implement GraphMatcher agent
  - Interface with Graph_Engine for bipartite matching
  - Effort: M, Priority: P0
- [ ] 3.4.3: Implement ConstraintOptimizer agent
  - Use CPSAT_Boundary for capacity-constrained allocation
  - Effort: M, Priority: P0
- [ ] 3.4.4: Implement TrustCalculator agent
  - Compute trust scores from collaboration feedback history
  - Effort: M, Priority: P0
- [ ] 3.4.5: Implement trust score calculation algorithm
  - Weighted average of 5 feedback dimensions with exponential decay (6-month half-life)
  - Effort: M, Priority: P0
- [ ] 3.4.6: Implement B2BSupervisor agent (LangGraph)
  - Orchestrate BOM parsing → graph matching → constraint optimization
  - Effort: L, Priority: P0
- [ ] 3.4.7: Write unit tests for B2B matching logic
  - Test BOM parsing, trust score calculation
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- BOM parsed from natural language correctly
- Graph matches returned with quality scores
- CP-SAT optimizes allocation with capacity constraints
- Trust scores calculated from feedback with decay
- B2B Swarm coordinates sub-agents correctly
- Unit tests verify B2B logic

**Dependencies**: Task 3.2 (Graph Engine), Task 3.3 (CP-SAT B2B)

---

### Task 3.5: B2B Collaboration Lifecycle Management

**Description**: Implement collaboration tracking from proposal to completion

**Subtasks**:
- [ ] 3.5.1: Implement collaboration status state machine
  - States: Proposed, Accepted, Active, On Hold, Completed, Terminated
  - Effort: M, Priority: P0
- [ ] 3.5.2: Implement document sharing within collaborations
  - Upload/download agreements, invoices, certificates
  - Effort: M, Priority: P0
- [ ] 3.5.3: Implement messaging interface for partners
  - Real-time chat within collaboration context
  - Effort: L, Priority: P1
- [ ] 3.5.4: Implement collaboration metrics tracking
  - Orders fulfilled, transaction value, delivery time, quality incidents
  - Effort: M, Priority: P1
- [ ] 3.5.5: Implement automated reminders
  - Pending shipments, pending payments, pending reviews
  - Effort: M, Priority: P1
- [ ] 3.5.6: Implement feedback collection workflow
  - Trigger on Completed/Terminated status
  - Effort: M, Priority: P0
- [ ] 3.5.7: Write integration tests for collaboration lifecycle
  - Test status transitions, feedback collection
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Collaboration status transitions tracked correctly
- Documents shared between partners
- Messaging works in real-time
- Metrics tracked throughout collaboration
- Reminders sent automatically
- Feedback collected on completion
- Integration tests verify lifecycle management

**Dependencies**: Task 3.1 (B2B schema), Task 3.4 (B2B Swarm)

---

### Task 3.6: FastAPI Endpoints - B2B Collaboration

**Description**: Implement REST API endpoints for B2B matching and collaboration

**Subtasks**:
- [ ] 3.6.1: Implement POST /b2b/profiles endpoint
  - Create B2B profile with tier-specific fields
  - Effort: M, Priority: P0
- [ ] 3.6.2: Implement GET /b2b/profiles/{id} endpoint
  - Retrieve B2B profile details
  - Effort: S, Priority: P0
- [ ] 3.6.3: Implement POST /b2b/matches endpoint
  - Find matches using graph + CP-SAT
  - Effort: M, Priority: P0
- [ ] 3.6.4: Implement POST /b2b/collaborations endpoint
  - Create collaboration from accepted match
  - Effort: M, Priority: P0
- [ ] 3.6.5: Implement PUT /b2b/collaborations/{id}/status endpoint
  - Update collaboration status
  - Effort: S, Priority: P0
- [ ] 3.6.6: Implement POST /b2b/collaborations/{id}/feedback endpoint
  - Submit collaboration feedback
  - Effort: M, Priority: P0
- [ ] 3.6.7: Implement GET /b2b/collaborations endpoint
  - List all collaborations with filters
  - Effort: M, Priority: P0
- [ ] 3.6.8: Write API integration tests for B2B endpoints
  - Test matching, collaboration lifecycle, feedback
  - Effort: L, Priority: P1

**Acceptance Criteria**:
- All B2B endpoints return correct responses
- Matching uses graph and CP-SAT correctly
- Collaboration lifecycle tracked through API
- Feedback submission updates trust scores
- API integration tests achieve 80%+ coverage

**Dependencies**: Task 3.4 (B2B Swarm), Task 3.5 (Collaboration Lifecycle)

---

## PHASE 4: FUNDING NAVIGATOR & INVESTOR READINESS (Category 4)

### Task 4.1: Investor Database Schema

**Description**: Implement investor database with preferences and portfolio

**Subtasks**:
- [ ] 4.1.1: Create investors table
  - Schema from design.md with ticket size, stages, sectors, geography
  - Effort: M, Priority: P0
- [ ] 4.1.2: Create funding_pipeline table
  - Track investor relationships through stages
  - Effort: M, Priority: P0
- [ ] 4.1.3: Create readiness_assessments table
  - Store dimension scores, overall readiness, gap recommendations
  - Effort: M, Priority: P0
- [ ] 4.1.4: Seed database with initial investors
  - Add sample angel investors, VCs, institutions
  - Effort: M, Priority: P1
- [ ] 4.1.5: Create database migration for funding tables
  - Alembic migration with indexes
  - Effort: S, Priority: P0

**Acceptance Criteria**:
- Investor tables created with preference fields
- Pipeline tracks investor relationships
- Readiness assessments stored with history
- Sample investors seeded in database
- Migrations run successfully

**Dependencies**: Task 1.2 (database setup)

---

### Task 4.2: Funding Readiness Assessment Engine

**Description**: Implement multi-dimensional funding readiness scoring

**Subtasks**:
- [ ] 4.2.1: Implement TeamStrengthAssessor
  - Score founder experience (0-20), team completeness (0-15), domain expertise (0-15), advisory board (0-10)
  - Effort: M, Priority: P0
- [ ] 4.2.2: Implement ProductMaturityAssessor
  - Score development stage, feature completeness, technical architecture, IP protection
  - Effort: M, Priority: P0
- [ ] 4.2.3: Implement MarketTractionAssessor
  - Score user acquisition, revenue generation, retention rate, partnerships, market validation
  - Effort: M, Priority: P0
- [ ] 4.2.4: Implement FinancialHealthAssessor
  - Score burn rate sustainability, revenue growth, unit economics, financial projections
  - Effort: M, Priority: P0
- [ ] 4.2.5: Implement PitchQualityAssessor
  - Score pitch deck completeness, problem-solution clarity, market opportunity, competitive differentiation
  - Effort: M, Priority: P0
- [ ] 4.2.6: Implement LegalComplianceAssessor
  - Score entity registration, DPIIT recognition, IP filings, regulatory compliance, cap table clarity
  - Effort: M, Priority: P0
- [ ] 4.2.7: Implement overall readiness score calculation
  - Weighted average: Team 20%, Product 20%, Traction 25%, Financial 15%, Pitch 10%, Legal 10%
  - Effort: S, Priority: P0
- [ ] 4.2.8: Implement readiness category classification
  - Not Ready (0-40), Developing (41-60), Ready (61-80), Highly Ready (81-100)
  - Effort: S, Priority: P0
- [ ] 4.2.9: Write unit tests for readiness scoring
  - Test each dimension scorer, overall calculation
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- All 6 dimensions scored correctly (0-100)
- Overall readiness score computed with correct weights
- Readiness category assigned based on thresholds
- Unit tests verify scoring logic

**Dependencies**: Task 2.1 (Legal Validation for compliance scoring)

---

### Task 4.3: Gap Analysis and Recommendation Engine

**Description**: Implement gap identification and actionable recommendations

**Subtasks**:
- [ ] 4.3.1: Implement GapAnalyzer agent
  - Identify dimensions with scores < 60
  - Effort: M, Priority: P0
- [ ] 4.3.2: Implement recommendation generation for Team Strength gaps
  - Recommendations: add co-founders, build advisory board, hire key roles, complete training
  - Effort: M, Priority: P0
- [ ] 4.3.3: Implement recommendation generation for Product Maturity gaps
  - Recommendations: develop MVP, add features, file patents, improve documentation
  - Effort: M, Priority: P0
- [ ] 4.3.4: Implement recommendation generation for Market Traction gaps
  - Recommendations: customer acquisition strategies, pilot programs, partnerships, case studies
  - Effort: M, Priority: P0
- [ ] 4.3.5: Implement recommendation generation for Financial Health gaps
  - Recommendations: extend runway, accelerate revenue, refine pricing, validate financial model
  - Effort: M, Priority: P0
- [ ] 4.3.6: Implement recommendation generation for Pitch Quality gaps
  - Recommendations: use templates, improve storytelling, enhance visualizations, practice pitching
  - Effort: M, Priority: P0
- [ ] 4.3.7: Implement recommendation generation for Legal Compliance gaps
  - Recommendations: register entity, apply for DPIIT, file trademarks, organize cap table
  - Effort: M, Priority: P0
- [ ] 4.3.8: Implement impact and effort estimation
  - Impact: Low (1-3 pts), Medium (4-7 pts), High (8+ pts)
  - Effort: Low (1-2 weeks), Medium (3-6 weeks), High (7+ weeks)
  - Effort: M, Priority: P0
- [ ] 4.3.9: Implement recommendation prioritization
  - Sort by impact-to-effort ratio (highest first)
  - Effort: S, Priority: P0
- [ ] 4.3.10: Write unit tests for gap analysis and recommendations
  - Test recommendation generation for various gap scenarios
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Gaps identified for dimensions < 60
- Recommendations generated with 3-5 actions per gap
- Impact and effort estimated for each recommendation
- Recommendations sorted by impact-to-effort ratio
- Unit tests verify recommendation logic

**Dependencies**: Task 4.2 (Readiness Assessment)

---


### Task 4.4: CP-SAT Investor Matching

**Description**: Implement constraint-based investor-startup matching

**Subtasks**:
- [ ] 4.4.1: Extend CPSATBoundary for investor matching model
  - Decision variables: matched[i] for each investor
  - Effort: M, Priority: P0
- [ ] 4.4.2: Implement ticket size constraints
  - funding_need within investor min/max ticket size
  - Effort: S, Priority: P0
- [ ] 4.4.3: Implement stage matching constraints
  - startup_stage in investor preferred stages
  - Effort: S, Priority: P0
- [ ] 4.4.4: Implement sector matching constraints
  - startup_domain in investor target sectors
  - Effort: S, Priority: P0
- [ ] 4.4.5: Implement traction threshold constraints
  - user_count >= min_users, revenue >= min_revenue
  - Effort: S, Priority: P0
- [ ] 4.4.6: Implement exclusion constraints
  - startup_domain not in investor exclusions
  - Effort: S, Priority: P0
- [ ] 4.4.7: Implement readiness gate constraints
  - Seed: readiness >= 60, Series A+: readiness >= 70
  - Effort: S, Priority: P0
- [ ] 4.4.8: Implement post-solution fit score ranking
  - Sector alignment (30%), stage (25%), traction (20%), geography (15%), track record (10%)
  - Effort: M, Priority: P0
- [ ] 4.4.9: Write unit tests for investor matching constraints
  - Test each constraint type, fit score calculation
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- CP-SAT identifies all eligible investors
- All hard constraints enforced correctly
- Fit score ranks investors by alignment
- Unit tests verify constraint logic

**Dependencies**: Task 2.3 (CP-SAT Boundary), Task 4.1 (Investor schema)

---

### Task 4.5: Funding Swarm - Readiness and Investor Matching

**Description**: Implement Funding Swarm (Swarm F) for funding workflows

**Subtasks**:
- [ ] 4.5.1: Implement ReadinessAssessor agent
  - Coordinate all 6 dimension assessors in parallel
  - Effort: M, Priority: P0
- [ ] 4.5.2: Implement GapAnalyzer agent integration
  - Generate actionable recommendations for gaps
  - Effort: M, Priority: P0
- [ ] 4.5.3: Implement InvestorMatcher agent
  - Interface with CPSAT_Boundary for investor matching
  - Effort: M, Priority: P0
- [ ] 4.5.4: Implement PipelineManager agent
  - Track investor relationships through stages
  - Effort: M, Priority: P0
- [ ] 4.5.5: Implement FundingSupervisor agent (LangGraph)
  - Orchestrate readiness assessment → gap analysis → investor matching
  - Effort: L, Priority: P0
- [ ] 4.5.6: Write unit tests for Funding Swarm logic
  - Test readiness assessment workflow
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Funding Swarm assesses readiness across 6 dimensions
- Gap analysis generates recommendations
- Investor matching returns eligible investors
- Pipeline tracking works through stages
- Unit tests verify Funding Swarm logic

**Dependencies**: Task 4.2 (Readiness Assessment), Task 4.3 (Gap Analysis), Task 4.4 (Investor Matching)

---

### Task 4.6: Funding Pipeline Management

**Description**: Implement funding pipeline tracking and investor engagement

**Subtasks**:
- [ ] 4.6.1: Implement pipeline status state machine
  - States: Initial Contact, Pitch Scheduled, Pitch Delivered, Due Diligence, Term Sheet, Negotiation, Closed Won, Closed Lost
  - Effort: M, Priority: P0
- [ ] 4.6.2: Implement interaction logging
  - Log meetings, documents shared, questions asked, feedback received
  - Effort: M, Priority: P0
- [ ] 4.6.3: Implement automated reminders
  - Remind 24h before meetings, follow-up 2 days after
  - Effort: M, Priority: P1
- [ ] 4.6.4: Implement pipeline metrics calculation
  - Total contacted, conversion rate by stage, average time per stage, pipeline value
  - Effort: M, Priority: P1
- [ ] 4.6.5: Implement Kanban board visualization API
  - Return pipeline organized by status columns
  - Effort: M, Priority: P1
- [ ] 4.6.6: Implement document management for funding
  - Upload pitch decks, financial models, due diligence docs, term sheets
  - Effort: M, Priority: P0
- [ ] 4.6.7: Write integration tests for pipeline management
  - Test status transitions, metrics calculation
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Pipeline status transitions tracked correctly
- Interactions logged with timestamps
- Reminders sent automatically
- Metrics calculated accurately
- Documents organized by investor
- Integration tests verify pipeline management

**Dependencies**: Task 4.1 (Funding schema)

---

### Task 4.7: FastAPI Endpoints - Funding and Investors

**Description**: Implement REST API endpoints for funding readiness and investor matching

**Subtasks**:
- [ ] 4.7.1: Implement POST /funding/readiness endpoint
  - Assess funding readiness across 6 dimensions
  - Effort: M, Priority: P0
- [ ] 4.7.2: Implement GET /funding/readiness/{startup_id} endpoint
  - Retrieve historical readiness assessments
  - Effort: S, Priority: P0
- [ ] 4.7.3: Implement POST /funding/investors/match endpoint
  - Match investors using CP-SAT constraints
  - Effort: M, Priority: P0
- [ ] 4.7.4: Implement GET /funding/investors endpoint
  - List investors with filters (type, stage, sector)
  - Effort: M, Priority: P0
- [ ] 4.7.5: Implement POST /funding/pipeline endpoint
  - Create pipeline entry for investor relationship
  - Effort: M, Priority: P0
- [ ] 4.7.6: Implement PUT /funding/pipeline/{id}/status endpoint
  - Update pipeline status
  - Effort: S, Priority: P0
- [ ] 4.7.7: Implement GET /funding/pipeline endpoint
  - Retrieve funding pipeline with metrics
  - Effort: M, Priority: P0
- [ ] 4.7.8: Write API integration tests for funding endpoints
  - Test readiness assessment, investor matching, pipeline tracking
  - Effort: L, Priority: P1

**Acceptance Criteria**:
- All funding endpoints return correct responses
- Readiness assessment returns dimension scores and gap recommendations
- Investor matching uses CP-SAT correctly
- Pipeline tracked through all stages
- API integration tests achieve 80%+ coverage

**Dependencies**: Task 4.5 (Funding Swarm), Task 4.6 (Pipeline Management)

---

## PHASE 5: OPTIMIZATION & LEARNING

### Task 5.1: Graph Neural Network for B2B Matching

**Description**: Implement GNN/LightGCN to improve B2B match quality over time

**Subtasks**:
- [ ] 5.1.1: Collect historical B2B match data
  - Store match outcomes (successful/unsuccessful) with collaboration feedback
  - Effort: M, Priority: P2
- [ ] 5.1.2: Implement LightGCN model architecture
  - Graph convolutional network for recommendation
  - Effort: L, Priority: P2
- [ ] 5.1.3: Implement training pipeline
  - Train on historical match data, optimize for match success prediction
  - Effort: L, Priority: P2
- [ ] 5.1.4: Implement inference for edge weight adjustment
  - Use learned embeddings to adjust edge weights
  - Effort: M, Priority: P2
- [ ] 5.1.5: Implement A/B testing framework
  - Compare GNN-adjusted weights vs. heuristic weights
  - Effort: M, Priority: P2
- [ ] 5.1.6: Write evaluation metrics (Precision@K, Recall@K, NDCG)
  - Evaluate match quality improvement
  - Effort: M, Priority: P2

**Acceptance Criteria**:
- LightGCN model trained on historical data
- Edge weights adjusted based on learned embeddings
- A/B testing shows improvement in match quality
- Evaluation metrics demonstrate better precision/recall

**Dependencies**: Task 3.2 (Graph Engine), Task 3.5 (Collaboration Feedback)

---

### Task 5.2: Analytics and Impact Dashboard

**Description**: Implement analytics dashboard for platform impact tracking

**Subtasks**:
- [ ] 5.2.1: Implement scheme application metrics
  - Total schemes applied, approval rate, total funding received
  - Effort: M, Priority: P1
- [ ] 5.2.2: Implement B2B collaboration metrics
  - Total collaborations formed, success rate, transaction value
  - Effort: M, Priority: P1
- [ ] 5.2.3: Implement funding metrics
  - Total funding rounds tracked, success rate, average time to close
  - Effort: M, Priority: P1
- [ ] 5.2.4: Implement user engagement metrics
  - Active users, session duration, feature usage
  - Effort: M, Priority: P1
- [ ] 5.2.5: Implement dashboard API endpoints
  - GET /analytics/schemes, GET /analytics/b2b, GET /analytics/funding, GET /analytics/users
  - Effort: M, Priority: P1
- [ ] 5.2.6: Implement data visualization components
  - Charts for trends, funnels, distributions
  - Effort: L, Priority: P2

**Acceptance Criteria**:
- All metrics calculated correctly from database
- Dashboard displays key impact indicators
- API endpoints return analytics data
- Visualizations render correctly

**Dependencies**: All previous phases (metrics from all modules)

---

### Task 5.3: Continuous Agent Evaluation and Rule Tuning

**Description**: Implement evaluation framework for multi-agent system quality

**Subtasks**:
- [ ] 5.3.1: Implement intent classification accuracy tracking
  - Log predicted vs. actual intents, calculate accuracy
  - Effort: M, Priority: P1
- [ ] 5.3.2: Implement swarm execution time monitoring
  - Track latency for each swarm operation
  - Effort: M, Priority: P1
- [ ] 5.3.3: Implement constraint solver performance tracking
  - Monitor CP-SAT solve times, infeasibility rates
  - Effort: M, Priority: P1
- [ ] 5.3.4: Implement user satisfaction feedback collection
  - Thumbs up/down, text feedback on recommendations
  - Effort: M, Priority: P1
- [ ] 5.3.5: Implement automated rule tuning
  - Adjust weights in relevance scoring based on feedback
  - Effort: L, Priority: P2
- [ ] 5.3.6: Implement alerting for degraded performance
  - Alert when accuracy drops, latency increases, or error rates spike
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- Intent classification accuracy tracked over time
- Swarm latency monitored and logged
- CP-SAT performance metrics recorded
- User feedback collected and analyzed
- Alerts triggered for performance degradation

**Dependencies**: All agent swarms (evaluation across entire system)

---

### Task 5.4: Security Hardening and Penetration Testing

**Description**: Implement security best practices and conduct security testing

**Subtasks**:
- [ ] 5.4.1: Implement SQL injection prevention tests
  - Verify parameterized queries prevent injection
  - Effort: M, Priority: P0
- [ ] 5.4.2: Implement XSS prevention
  - Sanitize all user inputs, implement CSP headers
  - Effort: M, Priority: P0
- [ ] 5.4.3: Implement CSRF protection
  - Add CSRF tokens to state-changing requests
  - Effort: M, Priority: P0
- [ ] 5.4.4: Implement encryption at rest
  - Encrypt sensitive fields (phone, DOB, caste, CIN, GSTIN) with AES-256
  - Effort: L, Priority: P0
- [ ] 5.4.5: Implement TLS 1.3 for all connections
  - Configure HTTPS with modern cipher suites
  - Effort: S, Priority: P0
- [ ] 5.4.6: Implement role-based access control (RBAC)
  - Define roles (user, admin), enforce permissions
  - Effort: M, Priority: P0
- [ ] 5.4.7: Conduct penetration testing
  - Hire external security firm or use automated tools (OWASP ZAP)
  - Effort: L, Priority: P1
- [ ] 5.4.8: Implement security audit logging
  - Log all authentication attempts, sensitive data access
  - Effort: M, Priority: P1

**Acceptance Criteria**:
- SQL injection tests pass (no tables dropped)
- XSS attempts blocked by sanitization
- CSRF tokens validated on all state-changing requests
- Sensitive data encrypted at rest
- All connections use TLS 1.3
- RBAC enforces correct permissions
- Penetration testing identifies no critical vulnerabilities
- Security events logged and auditable

**Dependencies**: All API endpoints (security applies across entire system)

---

### Task 5.5: Performance Testing and Optimization

**Description**: Conduct load testing and optimize for production scale

**Subtasks**:
- [ ] 5.5.1: Set up Locust load testing framework
  - Define user scenarios for scheme checking, B2B matching, funding assessment
  - Effort: M, Priority: P1
- [ ] 5.5.2: Conduct baseline performance tests
  - Measure 95th percentile latency, throughput, error rates
  - Effort: M, Priority: P1
- [ ] 5.5.3: Identify and optimize slow database queries
  - Use EXPLAIN ANALYZE, add indexes where needed
  - Effort: M, Priority: P1
- [ ] 5.5.4: Implement database connection pooling
  - Configure connection pool size, timeouts
  - Effort: S, Priority: P1
- [ ] 5.5.5: Implement API response caching
  - Cache GET requests with Redis (1-5 minute TTL)
  - Effort: M, Priority: P1
- [ ] 5.5.6: Optimize CP-SAT solver performance
  - Tune solver parameters, implement model caching
  - Effort: M, Priority: P1
- [ ] 5.5.7: Optimize embedding generation
  - Batch requests, cache embeddings aggressively
  - Effort: M, Priority: P1
- [ ] 5.5.8: Conduct stress testing
  - Test at 2x, 5x, 10x expected load
  - Effort: M, Priority: P1
- [ ] 5.5.9: Implement horizontal scaling
  - Deploy multiple API server instances behind load balancer
  - Effort: L, Priority: P2

**Acceptance Criteria**:
- 95th percentile latency < 500ms for eligibility checks
- 95th percentile latency < 1000ms for B2B matching
- Throughput: 1000 requests/second sustained
- Error rate < 0.1% under normal load
- System handles 5x expected load without degradation
- Horizontal scaling works with load balancer

**Dependencies**: All phases (performance testing across entire system)

---

### Task 5.6: Deployment and Infrastructure

**Description**: Implement production deployment infrastructure

**Subtasks**:
- [ ] 5.6.1: Containerize application with Docker
  - Create Dockerfile, docker-compose.yml for local development
  - Effort: M, Priority: P0
- [ ] 5.6.2: Set up Kubernetes cluster for production
  - Deploy on AWS EKS, GCP GKE, or Azure AKS
  - Effort: L, Priority: P1
- [ ] 5.6.3: Implement CI/CD pipeline
  - GitHub Actions or GitLab CI for automated testing and deployment
  - Effort: M, Priority: P1
- [ ] 5.6.4: Set up monitoring and alerting
  - Prometheus + Grafana for metrics, PagerDuty for alerts
  - Effort: M, Priority: P1
- [ ] 5.6.5: Implement log aggregation
  - ELK stack (Elasticsearch, Logstash, Kibana) or CloudWatch
  - Effort: M, Priority: P1
- [ ] 5.6.6: Implement backup and disaster recovery
  - Automated daily backups, cross-region replication
  - Effort: M, Priority: P1
- [ ] 5.6.7: Implement blue-green deployment
  - Zero-downtime deployments with rollback capability
  - Effort: M, Priority: P2
- [ ] 5.6.8: Conduct disaster recovery drill
  - Test backup restoration, failover procedures
  - Effort: M, Priority: P2

**Acceptance Criteria**:
- Application runs in Docker containers
- Kubernetes cluster deployed in production
- CI/CD pipeline deploys on every merge to main
- Monitoring dashboards display key metrics
- Logs aggregated and searchable
- Backups automated and tested
- Deployments have zero downtime
- Disaster recovery drill completes successfully

**Dependencies**: All previous tasks (deployment of complete system)

---

### Task 5.7: Documentation and User Guides

**Description**: Create comprehensive documentation for users and developers

**Subtasks**:
- [ ] 5.7.1: Write API documentation (OpenAPI/Swagger)
  - Document all endpoints with examples, schemas
  - Effort: M, Priority: P1
- [ ] 5.7.2: Write developer setup guide
  - Instructions for local development environment setup
  - Effort: M, Priority: P1
- [ ] 5.7.3: Write architecture documentation
  - System architecture diagrams, component descriptions
  - Effort: M, Priority: P1
- [ ] 5.7.4: Write user guides for each category
  - Ideation & Roadmap, Registered Startup, B2B Collaboration, Funding
  - Effort: L, Priority: P1
- [ ] 5.7.5: Create video tutorials
  - Walkthrough videos for key user journeys
  - Effort: L, Priority: P2
- [ ] 5.7.6: Write troubleshooting guide
  - Common issues and solutions
  - Effort: M, Priority: P2
- [ ] 5.7.7: Create FAQ section
  - Frequently asked questions with answers
  - Effort: M, Priority: P2

**Acceptance Criteria**:
- API documentation available at /docs endpoint
- Developer setup guide enables new developers to start in <1 hour
- Architecture documentation explains all major components
- User guides cover all 4 categories with screenshots
- Video tutorials demonstrate key workflows
- Troubleshooting guide resolves common issues

**Dependencies**: All previous tasks (documentation of complete system)

---

## Summary

**Total Tasks**: 180+ granular implementation tasks across 5 phases

**Critical Path**:
1. Phase 1 foundation (Tasks 1.1-1.9) → 6-8 weeks
2. Phase 2 schemes (Tasks 2.1-2.7) → 4-6 weeks
3. Phase 3 B2B (Tasks 3.1-3.6) → 4-6 weeks
4. Phase 4 funding (Tasks 4.1-4.7) → 4-6 weeks
5. Phase 5 optimization (Tasks 5.1-5.7) → 4-6 weeks

**Total Estimated Timeline**: 22-32 weeks (5.5-8 months) for MVP with all core features

**Team Size Recommendation**: 
- 2-3 Backend Engineers (Python, FastAPI, PostgreSQL)
- 1-2 ML Engineers (LangGraph, IndicBERT, OR-Tools)
- 1 Frontend Engineer (React, multilingual UI)
- 1 DevOps Engineer (Kubernetes, CI/CD)
- 1 QA Engineer (Testing, automation)
- 1 Technical Writer (Documentation)

**Technology Stack**:
- **Backend**: Python 3.10+, FastAPI, PostgreSQL 15+ (pgvector), Redis
- **AI/ML**: LangGraph, Transformers (IndicBERT), IndicTrans2, OpenAI API
- **Optimization**: OR-Tools CP-SAT, NetworkX, LightGCN (optional)
- **Storage**: S3 (MinIO/AWS), PostgreSQL
- **Deployment**: Docker, Kubernetes, GitHub Actions
- **Monitoring**: Prometheus, Grafana, ELK Stack

This comprehensive task breakdown provides an actionable, phase-by-phase implementation plan for Tamil Nadu StartupOS (Vanigam) from foundation to production deployment.
