# Requirements Document: Tamil Nadu StartupOS (Vanigam)

## Introduction

Tamil Nadu StartupOS (Vanigam) is a comprehensive multi-agent AI platform designed to support startup founders throughout their entrepreneurial journey in Tamil Nadu, India. The platform combines advanced AI techniques including LangGraph-based multi-agent swarms, CP-SAT constraint programming, and NetworkX graph-based matching to provide intelligent guidance across four core categories: Ideation & Roadmap, Registered Startup Journey, B2B Collaboration Hub, and Funding & Investor Readiness.

The system serves as a unified operating system for startups, providing personalized scheme recommendations, legal validation, B2B partner matching, funding readiness assessment, and investor connections. It supports multilingual interaction (English, Tamil, Hindi) with voice capabilities and enforces hard constraints through constraint programming to ensure compliance with government schemes, legal requirements, and business rules.

## Glossary

### System Components

- **Vanigam_Platform**: The complete Tamil Nadu StartupOS platform encompassing all four categories and multi-agent architecture
- **Central_Orchestrator**: The LangGraph-based supervisor agent that coordinates all swarm activities and manages conversation flow
- **CPSAT_Boundary**: The OR-Tools CP-SAT constraint programming engine that enforces hard constraints for eligibility, capacity, and matching
- **Profile_Swarm**: Multi-agent swarm (Swarm 1) responsible for founder profile creation, verification, and completeness scoring
- **Scheme_Swarm**: Multi-agent swarm (Swarm 2) responsible for scheme intelligence, eligibility checking, and recommendations
- **B2B_Swarm**: Multi-agent swarm (Swarm 3) responsible for B2B collaboration matching and trust scoring
- **Roadmap_Swarm**: Multi-agent swarm (Swarm 4) responsible for idea validation, roadmap generation, and milestone tracking
- **Funding_Swarm**: Multi-agent swarm (Swarm F) responsible for funding readiness assessment and investor matching
- **Document_Verifier**: Component that performs OCR, document validation, and authenticity checks
- **Legal_Validator**: Component that validates startup registration through MCA21, DPIIT, and GST registries
- **Graph_Engine**: NetworkX-based bipartite graph matching engine for B2B collaboration
- **Embedding_Service**: IndicBERT-based multilingual embedding service for semantic search and matching
- **Translation_Service**: IndicTrans2-based translation service for multilingual support

### Domain Entities

- **Founder**: An individual entrepreneur using the platform to build their startup
- **Startup**: A registered or unregistered business entity in the Tamil Nadu ecosystem
- **Scheme**: A government or institutional funding/support program with specific eligibility criteria
- **B2B_Partner**: A startup seeking or offering collaboration in raw materials, services, technology, or co-development
- **Investor**: An institutional or angel investor seeking startups for funding
- **Profile**: A structured data representation of a founder or startup including demographics, education, business details, and verification status
- **Roadmap**: A structured plan with milestones, timelines, and scheme annotations generated for a startup idea
- **Match**: A validated pairing between entities (B2B partners, startups and schemes, startups and investors)
- **Constraint_Model**: A CP-SAT mathematical model encoding eligibility rules, capacity limits, or matching criteria
- **Trust_Score**: A numerical score (0-100) representing reliability based on collaboration feedback and verification
- **Completeness_Score**: A categorical score (40/60/80/100%) representing profile data completeness
- **Readiness_Score**: A numerical score (0-100) representing funding readiness across multiple dimensions


### Technical Terms

- **LangGraph**: A framework for building stateful multi-agent applications with cyclic execution flows
- **CP-SAT**: Constraint Programming Satisfiability solver from OR-Tools for modeling and solving constraint satisfaction problems
- **NetworkX**: Python library for graph data structures and algorithms
- **IndicBERT**: Multilingual BERT model for Indic languages including Tamil and Hindi
- **IndicTrans2**: Neural machine translation model for Indic languages
- **pgvector**: PostgreSQL extension for vector similarity search
- **Bipartite_Graph**: A graph with two disjoint sets of nodes where edges only connect nodes from different sets
- **OCR**: Optical Character Recognition for extracting text from document images
- **MCA21**: Ministry of Corporate Affairs portal for company registration verification
- **DPIIT**: Department for Promotion of Industry and Internal Trade for startup recognition
- **GST**: Goods and Services Tax registration system
- **BOM**: Bill of Materials listing raw materials and components needed for production
- **First_Graduate**: A founder who is the first person in their family to complete graduation
- **Caste_Category**: Indian reservation categories (General, OBC, SC, ST, EWS)
- **Traction_Metrics**: Measurable indicators of business progress (users, revenue, partnerships)
- **Ticket_Size**: Investment amount range for a funding round or investor

### Business Terms

- **Ideation**: The initial phase where founders develop and validate startup ideas
- **Legal_Entity**: A registered business structure (Private Limited, LLP, OPC, Partnership, Proprietorship)
- **Scheme_Eligibility**: The set of criteria a startup must meet to qualify for a specific scheme
- **B2B_Tier**: Classification of collaboration types (T1: Raw Materials, T2: Services, T3: Tech/API, T4: Co-development)
- **Capacity_Constraint**: Physical or operational limits on production, service delivery, or collaboration
- **Funding_Stage**: Investment stage classification (Pre-seed, Seed, Series A/B/C)
- **Investor_Fit**: Alignment between startup characteristics and investor preferences
- **Scheme_Annotation**: Contextual scheme recommendations attached to specific roadmap milestones
- **Verification_Status**: State of document or entity validation (Pending, Verified, Rejected)
- **Collaboration_Feedback**: Structured evaluation of B2B partnership outcomes


## Requirements

---

## CATEGORY 1: IDEATION & ROADMAP

### Requirement 1.1: Founder Profile Creation and Completeness Scoring

**User Story:** As a founder, I want to create a comprehensive profile with my personal and educational details, so that the platform can provide personalized recommendations and verify my eligibility for schemes.

#### Acceptance Criteria

1. WHEN a founder registers on Vanigam_Platform, THE Profile_Swarm SHALL create a Founder Profile with demographic fields (name, age, gender, location, contact)
2. WHEN a founder provides educational details, THE Profile_Swarm SHALL capture highest qualification, institution, graduation year, and First_Graduate status
3. WHEN a founder provides caste category and supporting documents, THE Profile_Swarm SHALL store Caste_Category (General/OBC/SC/ST/EWS) with verification pending status
4. THE Profile_Swarm SHALL calculate Completeness_Score as 40% for basic demographics, 60% for demographics plus education, 80% for demographics plus education plus startup details, and 100% for all fields plus verified documents
5. WHEN Completeness_Score changes, THE Profile_Swarm SHALL update the score in the Profile and trigger re-evaluation of scheme eligibility by Scheme_Swarm
6. THE Vanigam_Platform SHALL support profile data entry in English, Tamil, and Hindi languages through Translation_Service
7. WHEN a founder uploads identity documents (Aadhaar, PAN), THE Document_Verifier SHALL extract text using OCR and validate document authenticity
8. IF document verification fails, THEN THE Document_Verifier SHALL return specific error messages indicating the reason for rejection

### Requirement 1.2: Startup Idea Validation and Structuring

**User Story:** As a founder, I want to describe my startup idea in natural language, so that the platform can validate its feasibility and structure it into a formal business concept.

#### Acceptance Criteria

1. WHEN a founder submits a startup idea in any supported language, THE Roadmap_Swarm SHALL translate the idea to English for processing using Translation_Service
2. THE Roadmap_Swarm SHALL extract key concept elements including problem statement, proposed solution, target market, value proposition, and competitive differentiation
3. THE Roadmap_Swarm SHALL validate idea completeness by checking for presence of all required concept elements
4. IF any concept element is missing, THEN THE Roadmap_Swarm SHALL ask clarifying questions to the founder
5. THE Roadmap_Swarm SHALL assess idea feasibility by analyzing market size, competition landscape, technical complexity, and regulatory barriers
6. THE Roadmap_Swarm SHALL assign a feasibility score from 0 to 100 based on market analysis, technical viability, and regulatory compliance
7. THE Roadmap_Swarm SHALL generate a structured idea document containing problem statement, solution description, target market definition, value proposition, and feasibility assessment
8. THE Vanigam_Platform SHALL store the structured idea document with timestamp and link it to the Founder Profile


### Requirement 1.3: Intelligent Roadmap Generation with Milestones

**User Story:** As a founder, I want an AI-generated roadmap with clear milestones and timelines, so that I have a structured plan to build my startup.

#### Acceptance Criteria

1. WHEN a structured idea is validated, THE Roadmap_Swarm SHALL generate a Roadmap with 5 to 15 milestones covering ideation through scaling phases
2. THE Roadmap_Swarm SHALL assign each milestone a phase label (Ideation, Validation, MVP, Launch, Growth, Scale), a specific goal description, deliverables list, and estimated timeline in months
3. THE Roadmap_Swarm SHALL sequence milestones in dependency order where prerequisite milestones must complete before dependent milestones can begin
4. THE Roadmap_Swarm SHALL identify critical path milestones that directly impact overall timeline and mark them as high priority
5. THE Roadmap_Swarm SHALL estimate resource requirements for each milestone including team size, funding needs, and key skills
6. WHEN generating timelines, THE Roadmap_Swarm SHALL consider startup domain, complexity, founder experience, and available resources
7. THE Roadmap_Swarm SHALL generate optimistic, realistic, and pessimistic timeline estimates for each milestone
8. THE Vanigam_Platform SHALL display the Roadmap as an interactive timeline with milestone dependencies and critical path visualization

### Requirement 1.4: Scheme Annotation on Roadmap Milestones

**User Story:** As a founder, I want to see relevant government schemes annotated on my roadmap milestones, so that I know when to apply for funding and support at each stage.

#### Acceptance Criteria

1. WHEN a Roadmap is generated, THE Scheme_Swarm SHALL analyze each milestone to identify applicable schemes based on milestone phase, funding needs, and founder profile
2. THE Scheme_Swarm SHALL retrieve scheme eligibility criteria from the scheme database for central government, Tamil Nadu state, and banking schemes
3. THE CPSAT_Boundary SHALL create a Constraint_Model encoding eligibility rules as boolean constraints on founder demographics, education, Caste_Category, Startup stage, domain, and funding requirements
4. THE CPSAT_Boundary SHALL solve the Constraint_Model to identify all schemes where the founder and milestone satisfy all eligibility constraints
5. THE Scheme_Swarm SHALL rank eligible schemes by relevance score computed from milestone-scheme alignment, funding amount match, and application deadline proximity
6. THE Scheme_Swarm SHALL annotate each milestone with the top 3 to 5 eligible schemes including scheme name, funding amount, key benefits, and application timeline
7. WHEN Completeness_Score increases, THE Scheme_Swarm SHALL re-run annotation to surface schemes that require higher profile completeness
8. THE Vanigam_Platform SHALL display scheme annotations as expandable cards on the roadmap timeline with direct links to application portals


### Requirement 1.5: Multilingual Voice Interaction for Idea Input

**User Story:** As a founder who is more comfortable speaking in Tamil, I want to describe my startup idea using voice input, so that I can interact naturally without typing in English.

#### Acceptance Criteria

1. THE Vanigam_Platform SHALL provide voice input capability in English, Tamil, and Hindi languages
2. WHEN a founder speaks their startup idea, THE Vanigam_Platform SHALL transcribe speech to text using language-specific speech recognition models
3. THE Translation_Service SHALL translate non-English input to English while preserving domain-specific terminology and context
4. THE Roadmap_Swarm SHALL process the translated text using the same idea validation logic as text input
5. THE Vanigam_Platform SHALL provide voice output in the founder's selected language for confirmations, questions, and guidance
6. THE Translation_Service SHALL translate system responses from English to the target language using IndicTrans2 models
7. THE Vanigam_Platform SHALL achieve translation accuracy of at least 85% for domain-specific startup terminology across all supported languages
8. IF transcription confidence is below 70%, THEN THE Vanigam_Platform SHALL ask the founder to repeat or provide text input

---

## CATEGORY 2: REGISTERED STARTUP JOURNEY

### Requirement 2.1: Legal Entity Validation and Registration Verification

**User Story:** As a registered startup, I want the platform to verify my legal entity registration, so that I can access schemes requiring registered startups and build trust with partners.

#### Acceptance Criteria

1. WHEN a startup provides a Corporate Identity Number (CIN), THE Legal_Validator SHALL query the MCA21 portal to retrieve company details including legal name, incorporation date, entity type, and status
2. WHEN a startup provides a DPIIT recognition number, THE Legal_Validator SHALL query the DPIIT startup database to verify recognition status, recognition date, and certificate validity
3. WHEN a startup provides a GST identification number (GSTIN), THE Legal_Validator SHALL query the GST portal to validate registration status, business type, and filing compliance
4. THE Legal_Validator SHALL update Verification_Status to Verified only when all provided legal identifiers are successfully validated against their respective registries
5. IF any legal identifier validation fails, THEN THE Legal_Validator SHALL set Verification_Status to Rejected and provide specific error details
6. THE Profile_Swarm SHALL update Completeness_Score to 100% when Legal_Entity verification status is Verified
7. THE Vanigam_Platform SHALL store validated legal entity details in the Startup profile with validation timestamp and source registry
8. THE Scheme_Swarm SHALL unlock scheme recommendations requiring registered entity status only after Verification_Status becomes Verified


### Requirement 2.2: Document Upload, OCR, and Verification

**User Story:** As a startup founder, I want to upload supporting documents like certificates, bank statements, and mark sheets, so that the platform can verify my eligibility for schemes requiring documentary proof.

#### Acceptance Criteria

1. THE Vanigam_Platform SHALL accept document uploads in PDF, JPG, PNG formats with maximum file size of 10MB per document
2. THE Document_Verifier SHALL support document types including Aadhaar card, PAN card, community certificate, GST certificate, Certificate of Incorporation, DPIIT certificate, educational mark sheets, and bank statements
3. WHEN a document is uploaded, THE Document_Verifier SHALL perform OCR to extract text content from the document image
4. THE Document_Verifier SHALL parse extracted text to identify document type, issuing authority, identification numbers, dates, and key data fields
5. THE Document_Verifier SHALL validate document authenticity by checking digital signatures, QR codes, watermarks, or cross-referencing with issuing authority databases where APIs are available
6. THE Document_Verifier SHALL extract structured data from documents including name matching founder profile name with 90% similarity threshold, date fields, numerical values, and categorical data
7. IF OCR confidence for any critical field is below 80%, THEN THE Document_Verifier SHALL flag the field for manual review by the founder
8. THE Vanigam_Platform SHALL store original document files in encrypted S3-compatible storage with access logging enabled
9. THE Profile_Swarm SHALL update relevant profile fields with verified document data and mark fields as document-verified
10. THE Scheme_Swarm SHALL use document-verified fields to evaluate eligibility for schemes requiring documentary proof such as First_Graduate status or Caste_Category

### Requirement 2.3: Comprehensive Scheme Database Management

**User Story:** As a scheme administrator, I want to maintain an up-to-date database of government and institutional schemes with structured eligibility criteria, so that startups receive accurate recommendations.

#### Acceptance Criteria

1. THE Vanigam_Platform SHALL maintain a scheme database containing central government schemes, Tamil Nadu state schemes, and banking/institutional schemes
2. THE Vanigam_Platform SHALL store for each Scheme the following fields: scheme name, scheme type (grant/loan/subsidy/incubation), funding agency, funding amount range, application deadline, scheme URL, and eligibility criteria
3. THE Vanigam_Platform SHALL encode eligibility criteria as structured rules on founder demographics (age range, gender, location), education (qualification level, First_Graduate status), Caste_Category, Startup characteristics (entity type, domain, stage, age, employee count, revenue range), and documentation requirements
4. THE Vanigam_Platform SHALL support compound eligibility rules using logical operators (AND, OR, NOT) to express complex criteria such as "First_Graduate AND (SC OR ST OR OBC)"
5. THE Vanigam_Platform SHALL store scheme benefit details including funding amount, interest rate, subsidy percentage, incubation duration, and mentorship provisions
6. THE Vanigam_Platform SHALL maintain scheme status (Active, Closed, Upcoming) and update based on application deadlines and agency announcements
7. THE Vanigam_Platform SHALL support scheme metadata including launch date, last update timestamp, total applicants, success rate, and disbursement timeline
8. THE Vanigam_Platform SHALL provide an administrative interface for scheme administrators to create, update, and deactivate scheme records


### Requirement 2.4: CP-SAT Based Scheme Eligibility Engine

**User Story:** As a startup, I want the platform to automatically determine all schemes I am eligible for based on hard constraints, so that I do not miss opportunities or waste time on ineligible schemes.

#### Acceptance Criteria

1. WHEN a startup requests scheme recommendations, THE CPSAT_Boundary SHALL create a Constraint_Model with boolean variables representing each scheme's eligibility
2. THE CPSAT_Boundary SHALL encode eligibility rules as constraints where each rule becomes a conjunction of boolean conditions on profile fields
3. THE CPSAT_Boundary SHALL model demographic constraints as range constraints (age between min and max), equality constraints (location equals Tamil Nadu), and set membership constraints (Caste_Category in allowed set)
4. THE CPSAT_Boundary SHALL model education constraints as level comparisons (qualification greater than or equal to minimum) and boolean checks (First_Graduate equals true)
5. THE CPSAT_Boundary SHALL model startup constraints as range constraints on age, revenue, employees, and categorical constraints on entity type, domain, and stage
6. THE CPSAT_Boundary SHALL model documentation constraints as boolean requirements where certain schemes require verified documents
7. THE CPSAT_Boundary SHALL solve the Constraint_Model to identify all schemes where all constraints are satisfied
8. THE CPSAT_Boundary SHALL return the set of eligible schemes with constraint satisfaction details indicating which criteria are met
9. IF the Constraint_Model is infeasible for a particular scheme, THEN THE CPSAT_Boundary SHALL identify which specific constraints are violated
10. THE Scheme_Swarm SHALL use CPSAT_Boundary results to filter schemes before applying ranking and relevance scoring

### Requirement 2.5: Personalized Scheme Recommendations with Ranking

**User Story:** As a startup founder, I want to see a ranked list of schemes most relevant to my current needs, so that I can prioritize applications and maximize my chances of success.

#### Acceptance Criteria

1. WHEN eligible schemes are identified by CPSAT_Boundary, THE Scheme_Swarm SHALL rank schemes by a composite relevance score
2. THE Scheme_Swarm SHALL compute relevance score as a weighted combination of funding amount match (30%), stage alignment (25%), domain fit (20%), deadline urgency (15%), and success rate (10%)
3. THE Scheme_Swarm SHALL calculate funding amount match as 100 minus absolute percentage difference between scheme amount and startup funding need
4. THE Scheme_Swarm SHALL calculate stage alignment by matching startup stage to scheme target stages (Pre-seed, Seed, Early, Growth)
5. THE Scheme_Swarm SHALL calculate domain fit using Embedding_Service to compute cosine similarity between startup domain description and scheme focus areas
6. THE Scheme_Swarm SHALL calculate deadline urgency as 100 times (days until deadline divided by 365) capped at 100
7. THE Scheme_Swarm SHALL retrieve scheme success rate from historical data as percentage of applicants who received funding
8. THE Scheme_Swarm SHALL present schemes sorted by relevance score in descending order with top 10 schemes displayed by default
9. THE Vanigam_Platform SHALL display for each recommended scheme: name, funding amount, deadline, key eligibility criteria met, relevance score, and a "Learn More" link
10. THE Vanigam_Platform SHALL allow founders to filter schemes by type (grant/loan/subsidy/incubation), funding range, and deadline range


### Requirement 2.6: Scheme Application Tracking and Status Updates

**User Story:** As a startup founder, I want to track the status of my scheme applications within the platform, so that I can follow up appropriately and manage multiple applications.

#### Acceptance Criteria

1. WHEN a founder initiates a scheme application, THE Vanigam_Platform SHALL create an application record with scheme ID, startup ID, application date, and status "In Progress"
2. THE Vanigam_Platform SHALL support application statuses including In Progress, Submitted, Under Review, Approved, Rejected, and Disbursed
3. THE Vanigam_Platform SHALL allow founders to upload completed application forms and supporting documents to the application record
4. THE Vanigam_Platform SHALL send reminder notifications 7 days and 1 day before scheme application deadlines
5. WHEN a founder manually updates application status, THE Vanigam_Platform SHALL record the status change with timestamp and optional notes
6. THE Vanigam_Platform SHALL display all scheme applications in a dashboard view with columns for scheme name, amount, status, deadline, and last updated date
7. THE Vanigam_Platform SHALL calculate and display aggregate statistics including total schemes applied, total funding requested, applications approved, and total funding received
8. THE Vanigam_Platform SHALL allow founders to add calendar events for application deadlines and interview dates

---

## CATEGORY 3: B2B COLLABORATION HUB

### Requirement 3.1: B2B Profile Creation with Bill of Materials

**User Story:** As a manufacturing startup, I want to create a B2B profile with my Bill of Materials and production needs, so that I can find suppliers and partners for raw materials and components.

#### Acceptance Criteria

1. THE Vanigam_Platform SHALL allow startups to create a B2B_Partner profile specifying their collaboration intent (Seeking, Offering, or Both)
2. WHEN a startup specifies collaboration intent, THE B2B_Swarm SHALL prompt for relevant details based on B2B_Tier categories (T1: Raw Materials, T2: Services, T3: Tech/API, T4: Co-development)
3. FOR Tier 1 Raw Materials, THE B2B_Swarm SHALL capture BOM including item name, specification, quantity required per month, unit of measure, quality standards, and acceptable price range
4. FOR Tier 2 Services, THE B2B_Swarm SHALL capture service type (legal, accounting, marketing, HR, logistics), service scope, frequency, and budget range
5. FOR Tier 3 Tech/API, THE B2B_Swarm SHALL capture technology needs (APIs, SDKs, platforms), integration requirements, data volume, and pricing model preference
6. FOR Tier 4 Co-development, THE B2B_Swarm SHALL capture partnership goals, IP sharing terms, resource contributions, and timeline
7. THE B2B_Swarm SHALL allow startups to specify capacity constraints including maximum order volume per month, minimum order quantity, lead time in days, and geographic service area
8. THE B2B_Swarm SHALL validate BOM entries for completeness and flag missing critical fields such as quantity or specifications
9. THE Vanigam_Platform SHALL store B2B_Partner profiles with timestamp and link them to the Startup profile


### Requirement 3.2: NetworkX Bipartite Graph Construction for B2B Matching

**User Story:** As the platform, I need to construct a bipartite graph of B2B demand and supply, so that I can efficiently match startups seeking resources with startups offering them.

#### Acceptance Criteria

1. WHEN B2B_Partner profiles are created or updated, THE Graph_Engine SHALL construct a Bipartite_Graph with two node sets: Demand nodes and Supply nodes
2. THE Graph_Engine SHALL create a Demand node for each startup seeking raw materials, services, technology, or co-development partners
3. THE Graph_Engine SHALL create a Supply node for each startup offering raw materials, services, technology, or co-development partnerships
4. THE Graph_Engine SHALL add edges between Demand and Supply nodes when there is a potential match based on category alignment (T1/T2/T3/T4)
5. THE Graph_Engine SHALL assign edge weights based on match quality computed from specification similarity, price compatibility, capacity alignment, and geographic proximity
6. THE Graph_Engine SHALL compute specification similarity using Embedding_Service to compare item descriptions and requirements with cosine similarity threshold of 0.7
7. THE Graph_Engine SHALL compute price compatibility as 100 minus absolute percentage difference between buyer budget and supplier price
8. THE Graph_Engine SHALL compute capacity alignment by checking if supplier maximum capacity exceeds buyer minimum quantity and supplier minimum quantity is below buyer maximum quantity
9. THE Graph_Engine SHALL compute geographic proximity as 100 minus (distance in kilometers divided by 10) for intra-state matches and apply 50% penalty for inter-state matches
10. THE Graph_Engine SHALL update the Bipartite_Graph incrementally when new B2B_Partner profiles are added or existing profiles are modified

### Requirement 3.3: Multi-Tier B2B Matching with CP-SAT Constraints

**User Story:** As a startup seeking raw materials, I want the platform to find the best suppliers who meet my specifications and capacity needs, so that I can establish reliable partnerships.

#### Acceptance Criteria

1. WHEN a startup requests B2B matches, THE B2B_Swarm SHALL identify the B2B_Tier (T1/T2/T3/T4) from their profile and retrieve relevant Demand or Supply nodes from Graph_Engine
2. THE Graph_Engine SHALL compute candidate matches as Supply nodes connected to the startup's Demand node with edge weight above 70
3. THE CPSAT_Boundary SHALL create a Constraint_Model to optimize match selection based on capacity constraints, exclusivity requirements, and geographic preferences
4. THE CPSAT_Boundary SHALL model capacity constraints as integer constraints ensuring total matched supply does not exceed demand quantity and individual supplier allocations respect minimum and maximum order quantities
5. THE CPSAT_Boundary SHALL model exclusivity constraints where certain startups require exclusive partnerships and cannot be matched with multiple partners in the same category
6. THE CPSAT_Boundary SHALL model geographic preferences as soft constraints with penalty costs for inter-state matches
7. THE CPSAT_Boundary SHALL maximize total match quality as the sum of edge weights for selected matches subject to all constraints
8. THE CPSAT_Boundary SHALL solve the Constraint_Model and return the optimal set of matches with partner assignments and allocated quantities
9. IF the Constraint_Model is infeasible due to insufficient supply or incompatible constraints, THEN THE CPSAT_Boundary SHALL relax soft constraints iteratively and report which constraints were relaxed
10. THE B2B_Swarm SHALL present matches to the startup ranked by match quality with partner details, specifications, pricing, and capacity information


### Requirement 3.4: Trust Score Calculation from Collaboration Feedback

**User Story:** As a startup evaluating potential B2B partners, I want to see trust scores based on past collaboration feedback, so that I can assess reliability before committing to a partnership.

#### Acceptance Criteria

1. WHEN a B2B collaboration completes or terminates, THE Vanigam_Platform SHALL prompt both parties to provide Collaboration_Feedback
2. THE Vanigam_Platform SHALL collect feedback on five dimensions: delivery timeliness (1-5 stars), quality of goods or services (1-5 stars), communication responsiveness (1-5 stars), pricing fairness (1-5 stars), and overall satisfaction (1-5 stars)
3. THE B2B_Swarm SHALL compute Trust_Score as a weighted average of feedback dimensions with weights: delivery timeliness 25%, quality 30%, communication 20%, pricing 15%, overall satisfaction 10%
4. THE B2B_Swarm SHALL normalize Trust_Score to a 0-100 scale where 0 represents 1 star across all dimensions and 100 represents 5 stars across all dimensions
5. THE B2B_Swarm SHALL aggregate Trust_Score across all collaborations for a startup using a weighted mean where recent collaborations have higher weight than older ones using exponential decay with half-life of 6 months
6. THE B2B_Swarm SHALL initialize Trust_Score to 50 for startups with no collaboration history
7. THE Vanigam_Platform SHALL display Trust_Score on B2B_Partner profiles as a numerical score and star rating
8. THE B2B_Swarm SHALL increase match edge weights by 20% for partners with Trust_Score above 80 and decrease by 20% for partners with Trust_Score below 30
9. THE Vanigam_Platform SHALL allow startups to view aggregated feedback statistics including number of collaborations, average rating per dimension, and feedback trends over time
10. THE Vanigam_Platform SHALL flag and investigate feedback submissions that deviate significantly from a startup's historical pattern to detect potential fraudulent reviews

### Requirement 3.5: B2B Collaboration Lifecycle Management

**User Story:** As a startup engaged in B2B collaborations, I want to manage partnerships through their lifecycle from initiation to completion, so that I have visibility and control over active relationships.

#### Acceptance Criteria

1. WHEN a startup accepts a B2B match, THE Vanigam_Platform SHALL create a collaboration record with partner IDs, collaboration type, agreed specifications, quantities, pricing, and start date
2. THE Vanigam_Platform SHALL support collaboration statuses including Proposed, Accepted, Active, On Hold, Completed, and Terminated
3. THE Vanigam_Platform SHALL allow partners to upload and share documents related to the collaboration including agreements, invoices, quality certificates, and shipment tracking
4. THE Vanigam_Platform SHALL provide a messaging interface for partners to communicate within the context of a specific collaboration
5. WHEN a collaboration status changes, THE Vanigam_Platform SHALL notify both partners and log the status change with timestamp and reason
6. THE Vanigam_Platform SHALL track collaboration metrics including total orders fulfilled, total transaction value, average delivery time, and quality incidents
7. THE Vanigam_Platform SHALL send automated reminders for pending actions such as pending shipments, pending payments, or pending quality reviews
8. WHEN a collaboration reaches Completed or Terminated status, THE Vanigam_Platform SHALL trigger the feedback collection workflow
9. THE Vanigam_Platform SHALL provide a dashboard view of all active collaborations with key metrics and status indicators
10. THE Vanigam_Platform SHALL allow startups to export collaboration data for accounting and reporting purposes


---

## CATEGORY 4: FUNDING & INVESTOR READINESS

### Requirement 4.1: Funding Readiness Assessment Across Multiple Dimensions

**User Story:** As a startup seeking funding, I want to understand my funding readiness across multiple dimensions, so that I can identify gaps and improve my chances of securing investment.

#### Acceptance Criteria

1. WHEN a startup requests funding readiness assessment, THE Funding_Swarm SHALL evaluate the startup across six dimensions: Team Strength, Product Maturity, Market Traction, Financial Health, Pitch Quality, and Legal Compliance
2. FOR Team Strength, THE Funding_Swarm SHALL score based on founder experience (0-20 points), team completeness (0-15 points), domain expertise (0-15 points), and advisory board strength (0-10 points) for a maximum of 60 points normalized to 0-100 scale
3. FOR Product Maturity, THE Funding_Swarm SHALL score based on development stage (Idea: 20, Prototype: 40, MVP: 60, Launched: 80, Scaling: 100), feature completeness (0-20 points), technical architecture robustness (0-20 points), and IP protection status (0-20 points)
4. FOR Market Traction, THE Funding_Swarm SHALL score based on user acquisition (0-25 points scaled by user count), revenue generation (0-25 points scaled by monthly revenue), customer retention rate (0-20 points), partnership quality (0-15 points), and market validation evidence (0-15 points)
5. FOR Financial Health, THE Funding_Swarm SHALL score based on burn rate sustainability (0-25 points), revenue growth trajectory (0-25 points), unit economics (0-20 points), and financial projections credibility (0-30 points)
6. FOR Pitch Quality, THE Funding_Swarm SHALL score based on pitch deck completeness (0-30 points with required slides), problem-solution clarity (0-25 points), market opportunity articulation (0-25 points), and competitive differentiation (0-20 points)
7. FOR Legal Compliance, THE Funding_Swarm SHALL score based on entity registration status (0-30 points), DPIIT recognition (0-20 points), IP filings (0-20 points), regulatory compliance (0-15 points), and cap table clarity (0-15 points)
8. THE Funding_Swarm SHALL compute overall Readiness_Score as the weighted average of dimension scores with weights: Team 20%, Product 20%, Traction 25%, Financial 15%, Pitch 10%, Legal 10%
9. THE Funding_Swarm SHALL classify readiness into categories: Not Ready (0-40), Developing (41-60), Ready (61-80), and Highly Ready (81-100)
10. THE Vanigam_Platform SHALL display readiness assessment as a spider chart showing all six dimensions with specific recommendations for improving low-scoring dimensions

### Requirement 4.2: Gap Analysis and Actionable Improvement Recommendations

**User Story:** As a startup with low funding readiness, I want specific recommendations on what to improve, so that I can take concrete actions to become investment-ready.

#### Acceptance Criteria

1. WHEN Readiness_Score is computed, THE Funding_Swarm SHALL identify dimensions with scores below 60 as gap areas requiring improvement
2. FOR each gap area, THE Funding_Swarm SHALL generate 3 to 5 specific actionable recommendations prioritized by impact on overall readiness
3. FOR Team Strength gaps, THE Funding_Swarm SHALL recommend actions such as adding co-founders with complementary skills, building advisory board, hiring key roles, or completing founder training programs
4. FOR Product Maturity gaps, THE Funding_Swarm SHALL recommend actions such as developing MVP, adding critical features, filing patent applications, or improving technical documentation
5. FOR Market Traction gaps, THE Funding_Swarm SHALL recommend actions such as customer acquisition strategies, pilot program launches, partnership development, or case study creation
6. FOR Financial Health gaps, THE Funding_Swarm SHALL recommend actions such as extending runway through cost optimization, revenue acceleration tactics, pricing model refinement, or financial model validation
7. FOR Pitch Quality gaps, THE Funding_Swarm SHALL recommend actions such as pitch deck template usage, storytelling improvements, data visualization enhancements, or pitch practice sessions
8. FOR Legal Compliance gaps, THE Funding_Swarm SHALL recommend actions such as entity registration, DPIIT recognition application, trademark filing, or cap table organization
9. THE Funding_Swarm SHALL estimate the impact of each recommendation as expected readiness score increase (Low: 1-3 points, Medium: 4-7 points, High: 8+ points)
10. THE Funding_Swarm SHALL estimate effort required for each recommendation (Low: 1-2 weeks, Medium: 3-6 weeks, High: 7+ weeks)
11. THE Vanigam_Platform SHALL display recommendations sorted by impact-to-effort ratio with highest priority actions at the top
12. THE Vanigam_Platform SHALL allow founders to mark recommendations as "In Progress" or "Completed" and track readiness improvement over time


### Requirement 4.3: Investor Database Management with Preferences

**User Story:** As an investor relations manager, I want to maintain a database of investors with their investment preferences, so that startups can be matched with relevant investors.

#### Acceptance Criteria

1. THE Vanigam_Platform SHALL maintain an investor database containing angel investors, venture capital firms, corporate venture arms, and institutional investors
2. THE Vanigam_Platform SHALL store for each Investor: investor name, investor type (Angel/VC/Corporate/Institution), contact details, portfolio URL, and investment track record
3. THE Vanigam_Platform SHALL capture investment preferences including Ticket_Size range (minimum and maximum investment amount), preferred Funding_Stage (Pre-seed/Seed/Series A/B/C), target sectors and domains, geographic focus, and investment thesis
4. THE Vanigam_Platform SHALL store investor portfolio details including number of active investments, total portfolio value, notable exits, and average investment hold period
5. THE Vanigam_Platform SHALL capture investor evaluation criteria including required Traction_Metrics thresholds (minimum users, minimum revenue), team composition preferences, and technology preferences
6. THE Vanigam_Platform SHALL support investor availability status (Actively Investing, Selective, Not Investing) and update based on investor input or market intelligence
7. THE Vanigam_Platform SHALL store investor success metrics including deal conversion rate, average time to investment decision, and founder satisfaction ratings
8. THE Vanigam_Platform SHALL provide an administrative interface for investor relations managers to create, update, and manage investor records
9. THE Vanigam_Platform SHALL validate Ticket_Size ranges to ensure minimum amount is less than maximum amount and amounts are positive
10. THE Vanigam_Platform SHALL allow investors to specify exclusion criteria such as domains to avoid, competitive conflicts, or regulatory restrictions

### Requirement 4.4: CP-SAT Based Investor-Startup Matching

**User Story:** As a funding-ready startup, I want to be matched with investors whose preferences align with my startup characteristics, so that I can focus on the most promising investor conversations.

#### Acceptance Criteria

1. WHEN a startup requests investor matches, THE Funding_Swarm SHALL retrieve the startup's profile including domain, stage, funding need, Traction_Metrics, team details, and Readiness_Score
2. THE CPSAT_Boundary SHALL create a Constraint_Model with boolean variables representing potential matches between the startup and each investor in the database
3. THE CPSAT_Boundary SHALL encode hard constraints including: funding need falls within investor Ticket_Size range, startup stage matches investor preferred Funding_Stage, startup domain is in investor target sectors, and investor availability status is Actively Investing or Selective
4. THE CPSAT_Boundary SHALL encode traction constraints where startup Traction_Metrics meet or exceed investor minimum thresholds for users, revenue, and other key metrics
5. THE CPSAT_Boundary SHALL encode exclusion constraints where startup domain or characteristics do not match investor exclusion criteria
6. THE CPSAT_Boundary SHALL encode readiness constraints requiring Readiness_Score to be at least 60 for Seed stage investors and at least 70 for Series A+ investors
7. THE CPSAT_Boundary SHALL solve the Constraint_Model to identify all investors where all hard constraints are satisfied
8. THE Funding_Swarm SHALL rank eligible investors by fit score computed from sector alignment (30%), stage alignment (25%), traction match (20%), geographic proximity (15%), and investor track record (10%)
9. THE Funding_Swarm SHALL compute sector alignment using Embedding_Service to measure cosine similarity between startup domain description and investor thesis
10. THE Funding_Swarm SHALL present top 10 matched investors with investor details, investment preferences, portfolio highlights, and contact information
11. IF no investors match due to constraint violations, THEN THE Funding_Swarm SHALL identify which constraints are most commonly violated and provide recommendations to meet investor requirements


### Requirement 4.5: Funding Pipeline Tracking and Investor Engagement

**User Story:** As a startup in discussions with multiple investors, I want to track my funding pipeline and manage investor relationships, so that I can coordinate the fundraising process effectively.

#### Acceptance Criteria

1. WHEN a startup initiates contact with an investor, THE Vanigam_Platform SHALL create a pipeline entry with investor ID, contact date, funding stage, and status "Initial Contact"
2. THE Vanigam_Platform SHALL support pipeline statuses including Initial Contact, Pitch Scheduled, Pitch Delivered, Due Diligence, Term Sheet, Negotiation, Closed Won, and Closed Lost
3. THE Vanigam_Platform SHALL allow startups to log interactions with investors including meeting notes, documents shared, questions asked, and feedback received
4. THE Vanigam_Platform SHALL send reminders for scheduled investor meetings 24 hours in advance and follow-up reminders 2 days after meetings
5. THE Vanigam_Platform SHALL calculate pipeline metrics including total investors contacted, conversion rate by stage, average time in each stage, and total funding pipeline value
6. THE Vanigam_Platform SHALL provide a Kanban board visualization of the funding pipeline with columns for each status and cards for each investor relationship
7. THE Vanigam_Platform SHALL allow startups to upload and organize pitch decks, financial models, due diligence documents, and term sheets linked to specific investors
8. WHEN a pipeline entry moves to Closed Won, THE Vanigam_Platform SHALL record investment amount, valuation, investor equity percentage, and investment date
9. WHEN a pipeline entry moves to Closed Lost, THE Vanigam_Platform SHALL record rejection reason and allow founders to add notes for future learning
10. THE Vanigam_Platform SHALL generate funding pipeline reports showing conversion funnel, stage durations, and success patterns to help founders optimize their fundraising strategy

---

## MULTI-AGENT ARCHITECTURE REQUIREMENTS

### Requirement 5.1: LangGraph Central Orchestrator for Conversation Management

**User Story:** As the platform, I need a central orchestrator to manage multi-turn conversations and coordinate between specialized swarms, so that user interactions are coherent and efficient.

#### Acceptance Criteria

1. THE Central_Orchestrator SHALL implement a LangGraph state machine with nodes representing conversation states including Greeting, Intent Recognition, Profile Collection, Idea Discussion, Roadmap Generation, Scheme Discovery, B2B Matching, Funding Assessment, and Clarification
2. THE Central_Orchestrator SHALL maintain conversation context including user ID, session ID, conversation history, current intent, extracted entities, and active swarm
3. WHEN a user message is received, THE Central_Orchestrator SHALL classify user intent into categories: Profile Update, Idea Input, Roadmap Request, Scheme Query, B2B Search, Funding Query, Document Upload, or General Question
4. THE Central_Orchestrator SHALL route requests to the appropriate specialized swarm based on intent classification: Profile_Swarm for profile operations, Roadmap_Swarm for ideation, Scheme_Swarm for schemes, B2B_Swarm for collaboration, Funding_Swarm for funding
5. THE Central_Orchestrator SHALL support multi-turn conversations where the swarm can ask clarifying questions and the orchestrator routes follow-up responses back to the same swarm
6. THE Central_Orchestrator SHALL maintain a conversation state stack to support context switching where a user can pause one task to ask about another and return to the original task
7. THE Central_Orchestrator SHALL implement timeout handling where conversations inactive for 30 minutes are suspended and context is saved for resumption
8. THE Central_Orchestrator SHALL log all conversation turns including user messages, swarm responses, intent classifications, and state transitions for debugging and analytics
9. THE Central_Orchestrator SHALL handle errors gracefully by catching swarm exceptions, logging errors, and providing user-friendly error messages without exposing internal details
10. THE Central_Orchestrator SHALL implement conversation guardrails to detect and reject inappropriate requests, PII leakage attempts, or attempts to manipulate swarm behavior


### Requirement 5.2: Specialized Agent Swarms with Internal Coordination

**User Story:** As a specialized swarm, I need to coordinate multiple sub-agents to complete complex tasks, so that I can provide comprehensive responses to user requests.

#### Acceptance Criteria

1. THE Profile_Swarm SHALL coordinate sub-agents for profile data collection, document verification, completeness scoring, and validation with each sub-agent handling a specific profile aspect
2. THE Scheme_Swarm SHALL coordinate sub-agents for scheme retrieval, eligibility checking via CPSAT_Boundary, ranking, and explanation generation
3. THE B2B_Swarm SHALL coordinate sub-agents for BOM parsing, graph matching via Graph_Engine, constraint optimization via CPSAT_Boundary, and trust score calculation
4. THE Roadmap_Swarm SHALL coordinate sub-agents for idea extraction, feasibility analysis, milestone generation, dependency resolution, and scheme annotation via Scheme_Swarm
5. THE Funding_Swarm SHALL coordinate sub-agents for readiness assessment, gap analysis, recommendation generation, investor matching via CPSAT_Boundary, and pipeline management
6. EACH specialized swarm SHALL implement a supervisor agent that orchestrates sub-agents, manages task distribution, aggregates results, and formats responses
7. EACH swarm supervisor SHALL support parallel execution of independent sub-agents to minimize latency for tasks such as document verification and data retrieval
8. EACH swarm supervisor SHALL implement retry logic with exponential backoff for sub-agent failures up to 3 attempts before escalating to Central_Orchestrator
9. EACH swarm supervisor SHALL track sub-agent execution time and flag slow operations exceeding 5 seconds for performance monitoring
10. EACH swarm supervisor SHALL validate sub-agent outputs for completeness and consistency before returning results to Central_Orchestrator

### Requirement 5.3: CP-SAT Boundary Engine for Constraint Enforcement

**User Story:** As the platform, I need a dedicated constraint programming engine to enforce hard constraints across all matching and eligibility decisions, so that recommendations are always valid and compliant.

#### Acceptance Criteria

1. THE CPSAT_Boundary SHALL provide a unified API for creating Constraint_Model instances with methods for adding variables, constraints, and objectives
2. THE CPSAT_Boundary SHALL support boolean variables, integer variables with domain ranges, and constraint types including equality, inequality, set membership, logical operators (AND, OR, NOT), and linear combinations
3. THE CPSAT_Boundary SHALL support optimization objectives including maximize, minimize, and multi-objective optimization with weighted sums
4. THE CPSAT_Boundary SHALL invoke the OR-Tools CP-SAT solver to find feasible solutions satisfying all constraints or prove infeasibility
5. THE CPSAT_Boundary SHALL return solution results including satisfiability status (Optimal, Feasible, Infeasible), variable assignments, objective value, and solver statistics (time, conflicts, branches)
6. IF a Constraint_Model is infeasible, THEN THE CPSAT_Boundary SHALL compute an irreducible infeasible subset (IIS) identifying minimal conflicting constraints
7. THE CPSAT_Boundary SHALL support constraint relaxation where soft constraints can be violated with penalties and the solver minimizes total penalty
8. THE CPSAT_Boundary SHALL implement caching for frequently-used constraint models such as scheme eligibility rules to avoid recomputation
9. THE CPSAT_Boundary SHALL enforce solver timeouts of 10 seconds for interactive queries and 60 seconds for batch operations
10. THE CPSAT_Boundary SHALL log all constraint model constructions, solutions, and infeasibilities for debugging and constraint tuning


### Requirement 5.4: NetworkX Graph Engine for B2B Matching

**User Story:** As the B2B matching system, I need a graph processing engine to construct and query bipartite graphs efficiently, so that I can find optimal partner matches at scale.

#### Acceptance Criteria

1. THE Graph_Engine SHALL use NetworkX to construct Bipartite_Graph data structures with two node sets and weighted edges
2. THE Graph_Engine SHALL support graph operations including add node, remove node, add edge, remove edge, update edge weight, and query neighbors
3. THE Graph_Engine SHALL implement bipartite matching algorithms including maximum weight matching and top-k matches per node
4. THE Graph_Engine SHALL compute maximum weight matching using NetworkX bipartite matching algorithms to find globally optimal match assignments
5. THE Graph_Engine SHALL compute top-k matches for a given node by sorting neighbors by edge weight in descending order and returning the top k nodes
6. THE Graph_Engine SHALL support graph persistence by serializing graph structures to PostgreSQL using adjacency list representation
7. THE Graph_Engine SHALL support incremental graph updates where adding or removing B2B_Partner profiles updates the graph without full reconstruction
8. THE Graph_Engine SHALL implement graph analytics including node degree distribution, average edge weight, connected components, and graph density
9. THE Graph_Engine SHALL optimize graph queries by indexing nodes by attributes such as domain, location, and tier for filtered neighbor retrieval
10. THE Graph_Engine SHALL handle large graphs with up to 100,000 nodes and 1 million edges with query response times under 1 second

### Requirement 5.5: Multilingual Embedding and Translation Services

**User Story:** As a user interacting in Tamil, I need the platform to understand my inputs and respond in Tamil, so that I can use the platform naturally in my preferred language.

#### Acceptance Criteria

1. THE Embedding_Service SHALL use IndicBERT models to generate 768-dimensional embeddings for text in English, Tamil, and Hindi
2. THE Embedding_Service SHALL support embedding operations for single texts and batch texts with batch sizes up to 100 for efficient processing
3. THE Embedding_Service SHALL compute cosine similarity between embeddings with values ranging from -1 to 1 where values above 0.7 indicate high similarity
4. THE Embedding_Service SHALL cache embeddings for frequently-used texts such as scheme descriptions and domain categories using Redis with TTL of 7 days
5. THE Translation_Service SHALL use IndicTrans2 models to translate text between English, Tamil, and Hindi bidirectionally
6. THE Translation_Service SHALL preserve domain-specific terminology by using a custom glossary for startup-related terms such as "funding", "scheme", "B2B", "roadmap"
7. THE Translation_Service SHALL achieve BLEU score of at least 40 for general translations and 35 for domain-specific translations
8. THE Translation_Service SHALL handle code-mixed inputs where users combine English and Indic languages in the same sentence
9. THE Translation_Service SHALL implement fallback to word-level translation when sentence-level translation fails
10. THE Vanigam_Platform SHALL store user language preference and automatically translate all system responses to the preferred language


---

## DATA MODEL AND STORAGE REQUIREMENTS

### Requirement 6.1: Founder and Startup Profile Data Model

**User Story:** As the platform, I need a comprehensive data model to store founder and startup information, so that all swarms can access consistent and complete profile data.

#### Acceptance Criteria

1. THE Vanigam_Platform SHALL implement a Founder entity with fields: founder_id (UUID), name, email, phone, date_of_birth, gender, location (state, district, city), highest_qualification, institution, graduation_year, first_graduate (boolean), caste_category, created_at, updated_at
2. THE Vanigam_Platform SHALL implement a Startup entity with fields: startup_id (UUID), founder_id (foreign key), startup_name, entity_type, cin_number, dpiit_number, gstin, domain, stage, incorporation_date, employee_count, monthly_revenue, created_at, updated_at
3. THE Vanigam_Platform SHALL implement a Profile_Completeness entity tracking completeness_score (40/60/80/100), missing_fields (array), verified_fields (array), last_updated
4. THE Vanigam_Platform SHALL implement a Document entity with fields: document_id (UUID), founder_id or startup_id, document_type, file_path, upload_date, verification_status, extracted_data (JSON), verifier_notes
5. THE Vanigam_Platform SHALL implement referential integrity constraints ensuring founders cannot be deleted while associated startups exist
6. THE Vanigam_Platform SHALL implement unique constraints on email, phone for founders and on cin_number, dpiit_number, gstin for startups
7. THE Vanigam_Platform SHALL index frequently-queried fields including founder email, startup domain, entity_type, and stage for fast retrieval
8. THE Vanigam_Platform SHALL implement soft deletes where entities are marked as deleted rather than physically removed to preserve audit trail
9. THE Vanigam_Platform SHALL encrypt sensitive fields including phone, date_of_birth, caste_category, cin_number, and gstin at rest using AES-256
10. THE Vanigam_Platform SHALL maintain an audit log table recording all create, update, delete operations on founder and startup entities with timestamp, user, and change details

### Requirement 6.2: Scheme Database Schema

**User Story:** As the platform, I need a structured scheme database to store government and institutional schemes with eligibility criteria, so that the constraint engine can evaluate matches efficiently.

#### Acceptance Criteria

1. THE Vanigam_Platform SHALL implement a Scheme entity with fields: scheme_id (UUID), scheme_name, scheme_type (grant/loan/subsidy/incubation), funding_agency, min_funding_amount, max_funding_amount, application_deadline, scheme_url, status (Active/Closed/Upcoming), created_at, updated_at
2. THE Vanigam_Platform SHALL implement a Scheme_Eligibility entity with fields: eligibility_id (UUID), scheme_id (foreign key), criterion_type (demographic/education/caste/startup/document), field_name, operator (equals/greater_than/less_than/in_set/between), value (JSON), required (boolean)
3. THE Vanigam_Platform SHALL represent compound eligibility rules using a Scheme_Eligibility_Group entity with fields: group_id (UUID), scheme_id (foreign key), logic_operator (AND/OR/NOT), parent_group_id (for nesting)
4. THE Vanigam_Platform SHALL implement a Scheme_Benefits entity with fields: benefit_id (UUID), scheme_id (foreign key), benefit_type, benefit_description, benefit_value
5. THE Vanigam_Platform SHALL implement a Scheme_Application entity tracking user applications with fields: application_id (UUID), scheme_id, startup_id, application_date, status, submitted_date, decision_date, funding_amount_approved
6. THE Vanigam_Platform SHALL implement cascade deletes where deleting a scheme removes associated eligibility criteria and benefits
7. THE Vanigam_Platform SHALL index scheme_name and funding_agency for text search and index application_deadline for deadline-based queries
8. THE Vanigam_Platform SHALL validate that min_funding_amount is less than or equal to max_funding_amount on insert and update
9. THE Vanigam_Platform SHALL automatically update scheme status to Closed when application_deadline passes using a scheduled job
10. THE Vanigam_Platform SHALL version scheme records to preserve historical eligibility criteria when schemes are updated

