# Design Document: Tamil Nadu StartupOS (Vanigam)

## Overview

### System Purpose

Tamil Nadu StartupOS (Vanigam) is an industrial-grade multi-agent AI platform designed to provide comprehensive support for startup founders throughout their entrepreneurial journey in Tamil Nadu. The platform integrates advanced AI technologies including LangGraph-based multi-agent swarms, CP-SAT constraint programming, NetworkX graph-based matching, and multilingual NLP to deliver intelligent, constraint-aware recommendations across four core categories.

### Core Capabilities

The platform provides:

1. **Ideation & Roadmap**: AI-guided idea validation, structured roadmap generation with milestone dependencies, and contextual scheme annotations
2. **Registered Startup Journey**: Legal entity verification, document processing with OCR, comprehensive scheme database, and CP-SAT based eligibility matching
3. **B2B Collaboration Hub**: Bill of Materials management, bipartite graph-based partner matching, constraint-optimized allocation, and trust scoring
4. **Funding & Investor Readiness**: Multi-dimensional readiness assessment, gap analysis with actionable recommendations, and constraint-based investor matching

### Key Differentiators

- **Constraint-First Architecture**: Hard constraints enforced through CP-SAT solver ensure all recommendations are mathematically proven valid
- **Multi-Agent Swarms**: LangGraph-coordinated agent swarms with specialized sub-agents for complex task decomposition and parallel execution
- **Graph-Native Matching**: NetworkX bipartite graphs with weighted edges for efficient B2B partner discovery and optimal matching
- **Multilingual Intelligence**: IndicBERT embeddings and IndicTrans2 translation for native Tamil and Hindi support with domain-specific terminology preservation
- **Industrial-Grade**: Production-ready architecture with PostgreSQL, Redis caching, S3 storage, comprehensive monitoring, and 99.9% uptime target


## Architecture

### High-Level System Architecture

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                          │
│  Web UI (React)  │  Mobile Apps  │  Voice Interface (Whisper) │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                   API Gateway & Auth Layer                      │
│    FastAPI │ JWT Auth │ Rate Limiting │ Request Validation     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│              LangGraph Central Orchestrator                     │
│   State Machine │ Intent Classification │ Context Management   │
└───┬──────┬──────┬──────┬──────┬─────────────────────────────────┘
    │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼
┌───────┬──────┬──────┬──────┬──────┐
│Profile│Scheme│ B2B  │Road- │Fund- │  Multi-Agent Swarms
│Swarm  │Swarm │Swarm │map   │ing   │  (LangGraph Supervisors)
│       │      │      │Swarm │Swarm │
└───┬───┴───┬──┴───┬──┴───┬──┴───┬──┘
    │       │      │      │      │
    ▼       ▼      ▼      ▼      ▼
┌───────────────────────────────────────────────────────────────┐
│                  Core Services Layer                          │
├─────────────────┬─────────────────┬──────────────────────────┤
│  CPSAT_Boundary │  Graph_Engine   │  Embedding_Service       │
│  (OR-Tools)     │  (NetworkX)     │  (IndicBERT)            │
├─────────────────┼─────────────────┼──────────────────────────┤
│Document_Verifier│ Legal_Validator │  Translation_Service     │
│(OCR + Validation)│ (MCA21/DPIIT)  │  (IndicTrans2)          │
└─────────────────┴─────────────────┴──────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                     Data Layer                                  │
├──────────────────┬─────────────────┬──────────────────────────┤
│   PostgreSQL     │   Redis Cache   │   S3 Storage             │
│ (Primary Data)   │ (Embeddings/    │ (Documents/Files)        │
│ + pgvector       │  Sessions)      │                          │
└──────────────────┴─────────────────┴──────────────────────────┘
```


### Multi-Agent Architecture

#### Central Orchestrator Design

The **Central_Orchestrator** is implemented as a LangGraph state machine that manages conversation flow and coordinates specialized swarms.

**LangGraph State Machine**:

```python
# State Definition
class ConversationState(TypedDict):
    user_id: str
    session_id: str
    messages: List[Message]
    current_intent: str
    extracted_entities: Dict[str, Any]
    active_swarm: Optional[str]
    context_stack: List[Dict]
    language_preference: str
    
# State Machine Nodes
nodes = {
    "greeting": greeting_node,
    "intent_recognition": intent_classifier_node,
    "profile_collection": profile_swarm_router,
    "idea_discussion": roadmap_swarm_router,
    "scheme_discovery": scheme_swarm_router,
    "b2b_matching": b2b_swarm_router,
    "funding_assessment": funding_swarm_router,
    "clarification": clarification_node,
    "error_handling": error_handler_node
}

# Conditional Edges Based on Intent
graph.add_conditional_edges(
    "intent_recognition",
    route_to_swarm,  # Function that routes based on classified intent
    {
        "profile": "profile_collection",
        "ideation": "idea_discussion",
        "schemes": "scheme_discovery",
        "b2b": "b2b_matching",
        "funding": "funding_assessment",
        "unclear": "clarification"
    }
)
```

**Intent Classification**:
- Uses fine-tuned IndicBERT classifier trained on startup domain conversations
- Multi-label classification supporting: Profile Update, Idea Input, Roadmap Request, Scheme Query, B2B Search, Funding Query, Document Upload, General Question
- Confidence threshold: 0.75 (routes to clarification if below)


#### Specialized Agent Swarms

Each swarm follows a consistent architecture pattern with a supervisor agent coordinating specialized sub-agents.

**Profile Swarm (Swarm 1)** - Founder profile management
- **Supervisor**: `ProfileSupervisor` - Orchestrates profile operations
- **Sub-Agents**:
  - `DataCollector`: Prompts for missing profile fields with multilingual support
  - `DocumentProcessor`: Routes documents to Document_Verifier, handles OCR results
  - `CompletenessScorer`: Calculates 40/60/80/100% score based on field presence
  - `Validator`: Cross-checks extracted document data with user-provided data
- **Execution**: Sequential for dependent operations (collect → verify → score), parallel for independent document processing

**Scheme Swarm (Swarm 2)** - Scheme intelligence and matching
- **Supervisor**: `SchemeSupervisor` - Manages scheme discovery workflow
- **Sub-Agents**:
  - `SchemeRetriever`: Queries scheme database with filters (type, deadline, amount)
  - `EligibilityChecker`: Interfaces with CPSAT_Boundary for constraint solving
  - `Ranker`: Computes relevance scores using embedding similarity and heuristics
  - `Explainer`: Generates natural language explanations for eligibility/ineligibility
- **Execution**: Parallel scheme retrieval and eligibility checking, sequential ranking

**B2B Swarm (Swarm 3)** - Collaboration matching
- **Supervisor**: `B2BSupervisor` - Manages B2B matching workflow
- **Sub-Agents**:
  - `BOMParser`: Extracts structured data from natural language BOMs
  - `GraphMatcher`: Interfaces with Graph_Engine for bipartite matching
  - `ConstraintOptimizer`: Uses CPSAT_Boundary for capacity-constrained allocation
  - `TrustCalculator`: Computes trust scores from collaboration feedback history
- **Execution**: Sequential BOM parsing → graph matching → constraint optimization


**Roadmap Swarm (Swarm 4)** - Idea validation and roadmap generation
- **Supervisor**: `RoadmapSupervisor` - Orchestrates roadmap creation
- **Sub-Agents**:
  - `IdeaExtractor`: Uses NLP to extract problem, solution, market, value proposition
  - `FeasibilityAnalyzer`: Assesses market size, competition, technical complexity
  - `MilestoneGenerator`: Creates phase-based milestones with dependencies
  - `SchemeAnnotator`: Calls Scheme_Swarm to annotate milestones with relevant schemes
- **Execution**: Sequential idea extraction → feasibility → milestone generation → annotation

**Funding Swarm (Swarm F)** - Funding readiness and investor matching
- **Supervisor**: `FundingSupervisor` - Manages funding workflows
- **Sub-Agents**:
  - `ReadinessAssessor`: Scores across 6 dimensions (Team, Product, Traction, Financial, Pitch, Legal)
  - `GapAnalyzer`: Identifies low-scoring dimensions and generates recommendations
  - `InvestorMatcher`: Uses CPSAT_Boundary for constraint-based investor matching
  - `PipelineManager`: Tracks investor relationships and pipeline stages
- **Execution**: Parallel readiness assessment across dimensions, sequential gap analysis

#### Swarm Communication Pattern

Swarms communicate through the Central_Orchestrator using a message-passing protocol:

```python
# Message Structure
class SwarmMessage(BaseModel):
    source_swarm: str
    target_swarm: Optional[str]
    message_type: str  # request, response, notification
    payload: Dict[str, Any]
    context: Dict[str, Any]
    
# Example: Roadmap Swarm requesting Scheme Swarm
roadmap_swarm.send_message(
    SwarmMessage(
        source_swarm="roadmap",
        target_swarm="scheme",
        message_type="request",
        payload={"milestone": milestone_data, "profile": founder_profile},
        context={"conversation_id": "...", "milestone_index": 3}
    )
)
```


## Components and Interfaces

### CPSAT_Boundary - Constraint Programming Engine

The CPSAT_Boundary provides a unified interface for constraint-based decision-making across three primary use cases: scheme eligibility, B2B matching, and investor matching.

#### Core Interface

```python
class CPSATBoundary:
    """Constraint programming engine using OR-Tools CP-SAT solver"""
    
    def create_model(self, model_type: str) -> ConstraintModel:
        """Factory method for creating typed constraint models"""
        
    def add_bool_var(self, model: ConstraintModel, name: str) -> BoolVar:
        """Add boolean decision variable"""
        
    def add_int_var(self, model: ConstraintModel, name: str, 
                    lb: int, ub: int) -> IntVar:
        """Add integer decision variable with domain [lb, ub]"""
        
    def add_constraint(self, model: ConstraintModel, 
                      constraint: Constraint) -> None:
        """Add hard constraint that must be satisfied"""
        
    def add_soft_constraint(self, model: ConstraintModel, 
                           constraint: Constraint, penalty: int) -> None:
        """Add soft constraint that can be violated with penalty"""
        
    def set_objective(self, model: ConstraintModel, 
                     objective: Objective) -> None:
        """Set optimization objective (maximize/minimize)"""
        
    def solve(self, model: ConstraintModel, 
             timeout_seconds: int = 10) -> SolverResult:
        """Solve constraint model and return results"""
        
    def compute_iis(self, model: ConstraintModel) -> List[Constraint]:
        """Compute irreducible infeasible subset for debugging"""
```


#### Scheme Eligibility Constraint Model

**Decision Variables**:
```python
# For each scheme s in scheme_database:
eligible[s] = BoolVar()  # True if startup is eligible for scheme s
```

**Hard Constraints** (examples):

1. **Age Constraint**: `(age >= min_age[s]) AND (age <= max_age[s]) => eligible[s]`
2. **Gender Constraint**: `(gender IN allowed_genders[s]) OR (eligible[s] == False)`
3. **Caste Category**: `(caste_category IN allowed_categories[s]) OR (eligible[s] == False)`
4. **First Graduate**: `(first_graduate == required_first_grad[s]) OR (eligible[s] == False)`
5. **Entity Type**: `(entity_type IN allowed_entities[s]) OR (eligible[s] == False)`
6. **Domain Match**: `(domain IN target_domains[s]) OR (eligible[s] == False)`
7. **Stage Match**: `(stage IN target_stages[s]) OR (eligible[s] == False)`
8. **Revenue Range**: `(revenue >= min_revenue[s]) AND (revenue <= max_revenue[s]) => eligible[s]`
9. **Employee Count**: `(employees >= min_employees[s]) AND (employees <= max_employees[s])`
10. **Document Verification**: `(required_docs[s] SUBSET verified_docs) OR (eligible[s] == False)`

**Compound Constraints** (example: "First Graduate AND (SC OR ST OR OBC)"):
```python
# Create auxiliary boolean variables
is_first_grad = (first_graduate == True)
is_reserved = (caste_category IN ['SC', 'ST', 'OBC'])

# Compound constraint
model.Add(eligible[scheme] <= is_first_grad)
model.Add(eligible[scheme] <= is_reserved)
```

**Objective**: None (feasibility problem - find all eligible schemes)

**Output**:
```python
@dataclass
class SchemeEligibilityResult:
    eligible_schemes: List[str]  # Scheme IDs that satisfy all constraints
    ineligible_schemes: Dict[str, List[str]]  # Scheme ID -> violated constraints
    solver_time_ms: float
```


#### B2B Matching Constraint Model

**Decision Variables**:
```python
# For each demand node d and supply node s:
match[d][s] = BoolVar()  # True if d is matched with s
allocation[d][s] = IntVar(0, max_quantity)  # Quantity allocated from s to d
```

**Hard Constraints**:

1. **Capacity Upper Bound**: `∀s: Σ_d allocation[d][s] <= supplier_max_capacity[s]`
2. **Capacity Lower Bound**: `∀s: (Σ_d match[d][s] > 0) => (Σ_d allocation[d][s] >= supplier_min_order[s])`
3. **Demand Satisfaction**: `∀d: Σ_s allocation[d][s] >= demand_quantity[d]`
4. **Match Activation**: `∀d,s: allocation[d][s] > 0 => match[d][s] == True`
5. **Minimum Order**: `∀d,s: match[d][s] == True => allocation[d][s] >= supplier_min_order[s]`
6. **Specification Match**: `∀d,s: match[d][s] == True => similarity(spec[d], spec[s]) >= 0.7`
7. **Price Compatibility**: `∀d,s: match[d][s] == True => supplier_price[s] <= buyer_budget[d]`
8. **Geographic Constraint**: `∀d,s: match[d][s] == True => distance(d, s) <= max_distance[d]`

**Soft Constraints** (with penalties):

1. **Inter-state Penalty**: Penalty of 50 points for inter-state matches
2. **Exclusivity Preference**: Penalty of 100 points if startup prefers exclusive but matched with multiple

**Objective**: `Maximize Σ_{d,s} match[d][s] * edge_weight[d][s] - penalties`

Where `edge_weight[d][s]` is computed from:
- Specification similarity (40%): cosine similarity of embeddings
- Price compatibility (30%): 100 - |buyer_budget - supplier_price| / buyer_budget * 100
- Capacity alignment (20%): min(1, supplier_capacity / demand_quantity)
- Geographic proximity (10%): 100 - distance_km / 10

**Output**:
```python
@dataclass
class B2BMatchResult:
    matches: List[Tuple[str, str, int]]  # (demand_id, supply_id, quantity)
    match_quality_score: float
    unmet_demand: Dict[str, int]  # demand_id -> unmet quantity
    relaxed_constraints: List[str]
```


#### Investor Matching Constraint Model

**Decision Variables**:
```python
# For each investor i:
matched[i] = BoolVar()  # True if investor i is eligible match for startup
```

**Hard Constraints**:

1. **Ticket Size**: `(funding_need >= investor_min_ticket[i]) AND (funding_need <= investor_max_ticket[i]) => matched[i]`
2. **Stage Match**: `(startup_stage IN investor_stages[i]) OR (matched[i] == False)`
3. **Sector Match**: `(startup_domain IN investor_sectors[i]) OR (matched[i] == False)`
4. **Availability**: `(investor_status[i] IN ['Actively Investing', 'Selective']) OR (matched[i] == False)`
5. **Traction Thresholds**: 
   - `(user_count >= min_users[i]) OR (matched[i] == False)`
   - `(revenue >= min_revenue[i]) OR (matched[i] == False)`
6. **Exclusions**: `(startup_domain NOT IN investor_exclusions[i]) OR (matched[i] == False)`
7. **Readiness Gate**: 
   - Seed investors: `(readiness_score >= 60) OR (matched[i] == False)`
   - Series A+ investors: `(readiness_score >= 70) OR (matched[i] == False)`
8. **Geographic Preference**: Soft constraint with penalty for non-preferred locations

**Objective**: None (feasibility - find all eligible investors)

**Post-Processing Ranking**:
After CP-SAT identifies eligible investors, rank by fit score:
```python
fit_score = (
    0.30 * sector_alignment +      # Cosine similarity of embeddings
    0.25 * stage_alignment +        # Exact match bonus
    0.20 * traction_match +         # (actual - required) / required
    0.15 * geographic_proximity +   # Same state bonus
    0.10 * investor_track_record    # Success rate * portfolio size
)
```

**Output**:
```python
@dataclass
class InvestorMatchResult:
    eligible_investors: List[str]
    fit_scores: Dict[str, float]
    violated_constraints: Dict[str, List[str]]  # investor_id -> constraints
```


### Graph_Engine - NetworkX Bipartite Matching

The Graph_Engine manages B2B collaboration matching using bipartite graphs with weighted edges.

#### Core Interface

```python
class GraphEngine:
    """NetworkX-based bipartite graph matching engine"""
    
    def __init__(self):
        self.graph: nx.Graph = nx.Graph()
        
    def add_demand_node(self, node_id: str, attributes: Dict) -> None:
        """Add demand-side node (startup seeking resources)"""
        
    def add_supply_node(self, node_id: str, attributes: Dict) -> None:
        """Add supply-side node (startup offering resources)"""
        
    def add_edge(self, demand_id: str, supply_id: str, weight: float) -> None:
        """Add weighted edge between demand and supply nodes"""
        
    def compute_edge_weight(self, demand: Dict, supply: Dict) -> float:
        """Compute match quality from specifications and constraints"""
        
    def get_top_k_matches(self, node_id: str, k: int = 10) -> List[Tuple[str, float]]:
        """Get top k highest-weight neighbors for a node"""
        
    def maximum_weight_matching(self) -> List[Tuple[str, str]]:
        """Compute globally optimal matching maximizing total weight"""
        
    def update_edge_weight(self, demand_id: str, supply_id: str, 
                          new_weight: float) -> None:
        """Update edge weight (e.g., based on trust score changes)"""
        
    def persist_graph(self, db_connection: Any) -> None:
        """Serialize graph to PostgreSQL adjacency list"""
        
    def load_graph(self, db_connection: Any) -> None:
        """Load graph from PostgreSQL"""
```



#### Edge Weight Computation Algorithm

```python
def compute_edge_weight(self, demand: Dict, supply: Dict) -> float:
    """
    Compute match quality score from four components:
    1. Specification similarity (40%)
    2. Price compatibility (30%)
    3. Capacity alignment (20%)
    4. Geographic proximity (10%)
    """
    # 1. Specification Similarity using IndicBERT embeddings
    demand_embedding = embedding_service.embed(demand['specification'])
    supply_embedding = embedding_service.embed(supply['offering'])
    cosine_sim = np.dot(demand_embedding, supply_embedding) / (
        np.linalg.norm(demand_embedding) * np.linalg.norm(supply_embedding)
    )
    spec_score = max(0, cosine_sim) * 100  # Normalize to 0-100
    
    # 2. Price Compatibility
    if supply['price'] <= demand['budget']:
        price_diff_pct = abs(supply['price'] - demand['budget']) / demand['budget']
        price_score = 100 - (price_diff_pct * 100)
    else:
        price_score = 0  # Over budget
    
    # 3. Capacity Alignment
    if supply['max_capacity'] >= demand['quantity'] >= supply['min_order']:
        capacity_ratio = min(1.0, supply['max_capacity'] / demand['quantity'])
        capacity_score = capacity_ratio * 100
    else:
        capacity_score = 0  # Cannot fulfill
    
    # 4. Geographic Proximity
    distance_km = calculate_distance(demand['location'], supply['location'])
    if demand['location']['state'] == supply['location']['state']:
        geo_score = max(0, 100 - (distance_km / 10))  # Intra-state
    else:
        geo_score = max(0, 50 - (distance_km / 20))  # Inter-state penalty
    
    # Weighted combination
    edge_weight = (
        0.40 * spec_score +
        0.30 * price_score +
        0.20 * capacity_score +
        0.10 * geo_score
    )
    
    return edge_weight
```

#### Maximum Weight Matching Algorithm

```python
def maximum_weight_matching(self) -> List[Tuple[str, str]]:
    """
    Compute globally optimal bipartite matching using NetworkX.
    Returns list of (demand_id, supply_id) pairs.
    """
    # NetworkX bipartite matching requires explicit node set labels
    demand_nodes = {n for n, d in self.graph.nodes(data=True) 
                    if d['bipartite'] == 0}
    supply_nodes = {n for n, d in self.graph.nodes(data=True) 
                    if d['bipartite'] == 1}
    
    # Compute maximum weight matching
    matching = nx.bipartite.maximum_matching(self.graph, demand_nodes, 
                                             supply_nodes)
    
    # Convert to list of demand-supply pairs
    matches = []
    for node, partner in matching.items():
        if node in demand_nodes:  # Only include demand->supply direction
            matches.append((node, partner))
    
    return matches
```


### Embedding_Service - Multilingual Semantic Understanding

The Embedding_Service provides multilingual embeddings using IndicBERT for semantic similarity and search.

#### Core Interface

```python
class EmbeddingService:
    """IndicBERT-based multilingual embedding service"""
    
    def __init__(self, model_name: str = "ai4bharat/indic-bert"):
        self.model = AutoModel.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.cache = RedisCache(ttl=7*24*60*60)  # 7 days
        
    def embed(self, text: str, language: str = "en") -> np.ndarray:
        """Generate 768-dim embedding for text"""
        
    def embed_batch(self, texts: List[str], 
                   language: str = "en") -> np.ndarray:
        """Batch embedding for efficiency (up to 100 texts)"""
        
    def cosine_similarity(self, emb1: np.ndarray, 
                         emb2: np.ndarray) -> float:
        """Compute cosine similarity between embeddings"""
        
    def semantic_search(self, query: str, corpus: List[str], 
                       top_k: int = 10) -> List[Tuple[int, float]]:
        """Search corpus for most similar texts to query"""
```

#### Implementation Details

**Caching Strategy**:
```python
def embed(self, text: str, language: str = "en") -> np.ndarray:
    # Generate cache key from text hash and language
    cache_key = f"emb:{language}:{hashlib.md5(text.encode()).hexdigest()}"
    
    # Check cache
    cached = self.cache.get(cache_key)
    if cached:
        return np.frombuffer(cached, dtype=np.float32)
    
    # Generate embedding
    inputs = self.tokenizer(text, return_tensors="pt", 
                           padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = self.model(**inputs)
        # Use [CLS] token embedding
        embedding = outputs.last_hidden_state[:, 0, :].numpy()[0]
    
    # Cache result
    self.cache.set(cache_key, embedding.tobytes())
    
    return embedding
```

**Semantic Search with pgvector**:
```python
def semantic_search_db(self, query: str, table: str, 
                      top_k: int = 10) -> List[Dict]:
    """
    Search PostgreSQL table with pgvector extension.
    Assumes table has 'embedding' column of type vector(768).
    """
    query_embedding = self.embed(query)
    
    # Use pgvector's <-> operator for L2 distance
    # or <#> for inner product, <=> for cosine distance
    sql = f"""
        SELECT *, embedding <=> %s::vector AS distance
        FROM {table}
        ORDER BY distance
        LIMIT %s
    """
    
    results = db.execute(sql, (query_embedding.tolist(), top_k))
    return results
```


### Translation_Service - Multilingual Content Translation

The Translation_Service uses IndicTrans2 for high-quality translation between English, Tamil, and Hindi.

#### Core Interface

```python
class TranslationService:
    """IndicTrans2-based translation service with domain glossary"""
    
    def __init__(self):
        self.model = load_indictrans2_model()
        self.glossary = self.load_domain_glossary()
        
    def translate(self, text: str, source_lang: str, 
                 target_lang: str) -> str:
        """Translate text preserving domain terminology"""
        
    def translate_with_fallback(self, text: str, source_lang: str,
                               target_lang: str) -> Tuple[str, float]:
        """Translate with confidence score, fallback if needed"""
        
    def load_domain_glossary(self) -> Dict[str, Dict[str, str]]:
        """Load startup domain term mappings"""
```

#### Domain Glossary

```python
DOMAIN_GLOSSARY = {
    "en": {
        "funding": {"ta": "நிதியளிப்பு", "hi": "फंडिंग"},
        "scheme": {"ta": "திட்டம்", "hi": "योजना"},
        "startup": {"ta": "தொடக்க நிறுவனம்", "hi": "स्टार्टअप"},
        "roadmap": {"ta": "பாதை வரைபடம்", "hi": "रोडमैप"},
        "B2B": {"ta": "வணிகம்-வணிகம்", "hi": "बी2बी"},
        "investor": {"ta": "முதலீட்டாளர்", "hi": "निवेशक"},
        "milestone": {"ta": "மைல்கல்", "hi": "माइलस्टोन"},
        "prototype": {"ta": "முன்மாதிரி", "hi": "प्रोटोटाइप"}
    }
}
```

#### Translation with Glossary Preservation

```python
def translate(self, text: str, source_lang: str, target_lang: str) -> str:
    """
    Translate text while preserving domain-specific terminology.
    Strategy: Replace glossary terms with placeholders, translate, restore.
    """
    # Step 1: Find and replace glossary terms with placeholders
    replacements = []
    modified_text = text
    for term, translations in self.glossary[source_lang].items():
        if term in text:
            placeholder = f"__TERM_{len(replacements)}__"
            modified_text = modified_text.replace(term, placeholder)
            replacements.append((placeholder, translations[target_lang]))
    
    # Step 2: Translate modified text
    translated = self.model.translate(modified_text, 
                                     src_lang=source_lang,
                                     tgt_lang=target_lang)
    
    # Step 3: Restore glossary terms in target language
    for placeholder, target_term in replacements:
        translated = translated.replace(placeholder, target_term)
    
    return translated
```


## Data Models

### Core Entities

#### Founder Profile

```python
from datetime import datetime
from uuid import UUID
from enum import Enum

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

class CasteCategory(str, Enum):
    GENERAL = "general"
    OBC = "obc"
    SC = "sc"
    ST = "st"
    EWS = "ews"


@dataclass
class Location:
    state: str
    district: str
    city: str
    pincode: Optional[str] = None

@dataclass
class FounderProfile:
    founder_id: UUID
    name: str
    email: str
    phone: str
    date_of_birth: datetime
    gender: Gender
    location: Location
    highest_qualification: str
    institution: str
    graduation_year: int
    first_graduate: bool
    caste_category: Optional[CasteCategory]
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    age: int
    completeness_score: int  # 40, 60, 80, or 100
```

**PostgreSQL Schema**:
```sql
CREATE TABLE founders (
    founder_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(50) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    pincode VARCHAR(10),
    highest_qualification VARCHAR(255),
    institution VARCHAR(255),
    graduation_year INTEGER,
    first_graduate BOOLEAN DEFAULT FALSE,
    caste_category VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,  -- Soft delete
    
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_phone CHECK (phone ~* '^\+?[1-9]\d{1,14}$')
);

CREATE INDEX idx_founders_email ON founders(email);
CREATE INDEX idx_founders_phone ON founders(phone);
CREATE INDEX idx_founders_location ON founders(state, district);
```

#### Startup Profile

```python
class EntityType(str, Enum):
    PRIVATE_LIMITED = "private_limited"
    LLP = "llp"
    OPC = "opc"
    PARTNERSHIP = "partnership"
    SOLE_PROPRIETOR = "sole_proprietor"

class StartupStage(str, Enum):
    IDEA = "idea"
    POC = "poc"
    PROTOTYPE = "prototype"
    MVP = "mvp"
    REVENUE = "revenue"
    GROWTH = "growth"
    SCALE = "scale"

@dataclass
class StartupProfile:
    startup_id: UUID
    founder_id: UUID
    startup_name: str
    entity_type: EntityType
    cin_number: Optional[str]
    dpiit_number: Optional[str]
    gstin: Optional[str]
    domain: str
    stage: StartupStage
    incorporation_date: Optional[datetime]
    employee_count: int
    monthly_revenue: Decimal
    created_at: datetime
    updated_at: datetime
    
    # Verification
    verification_status: str  # pending, verified, rejected
    legal_validated_at: Optional[datetime]
```

**PostgreSQL Schema**:
```sql
CREATE TABLE startups (
    startup_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID NOT NULL REFERENCES founders(founder_id) ON DELETE CASCADE,
    startup_name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    cin_number VARCHAR(21) UNIQUE,
    dpiit_number VARCHAR(100) UNIQUE,
    gstin VARCHAR(15) UNIQUE,
    domain VARCHAR(255) NOT NULL,
    stage VARCHAR(50) NOT NULL,
    incorporation_date DATE,
    employee_count INTEGER DEFAULT 0,
    monthly_revenue DECIMAL(15, 2) DEFAULT 0,
    verification_status VARCHAR(50) DEFAULT 'pending',
    legal_validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    CONSTRAINT valid_cin CHECK (cin_number IS NULL OR cin_number ~* '^[LUF][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$'),
    CONSTRAINT valid_gstin CHECK (gstin IS NULL OR LENGTH(gstin) = 15),
    CONSTRAINT positive_employees CHECK (employee_count >= 0),
    CONSTRAINT positive_revenue CHECK (monthly_revenue >= 0)
);

CREATE INDEX idx_startups_founder ON startups(founder_id);
CREATE INDEX idx_startups_domain ON startups(domain);
CREATE INDEX idx_startups_stage ON startups(stage);
CREATE INDEX idx_startups_verification ON startups(verification_status);
```

#### Scheme Entity

```python
class SchemeType(str, Enum):
    GRANT = "grant"
    LOAN = "loan"
    SUBSIDY = "subsidy"
    INCUBATION = "incubation"

class SchemeStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    UPCOMING = "upcoming"

@dataclass
class Scheme:
    scheme_id: UUID
    scheme_name: str
    scheme_type: SchemeType
    funding_agency: str
    min_funding_amount: Decimal
    max_funding_amount: Decimal
    application_deadline: datetime
    scheme_url: str
    status: SchemeStatus
    created_at: datetime
    updated_at: datetime
    
    # Eligibility criteria (stored as JSON in DB)
    eligibility_criteria: Dict[str, Any]
    
    # Benefits
    interest_rate: Optional[Decimal]
    subsidy_percentage: Optional[Decimal]
    incubation_duration_months: Optional[int]
```

**PostgreSQL Schema**:
```sql
CREATE TABLE schemes (
    scheme_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_name VARCHAR(500) NOT NULL,
    scheme_type VARCHAR(50) NOT NULL,
    funding_agency VARCHAR(255) NOT NULL,
    min_funding_amount DECIMAL(15, 2) NOT NULL,
    max_funding_amount DECIMAL(15, 2) NOT NULL,
    application_deadline TIMESTAMP NOT NULL,
    scheme_url TEXT,
    status VARCHAR(50) DEFAULT 'active',
    eligibility_criteria JSONB NOT NULL,  -- Flexible eligibility rules
    interest_rate DECIMAL(5, 2),
    subsidy_percentage DECIMAL(5, 2),
    incubation_duration_months INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_funding_range CHECK (min_funding_amount <= max_funding_amount),
    CONSTRAINT positive_funding CHECK (min_funding_amount > 0)
);

CREATE INDEX idx_schemes_type ON schemes(scheme_type);
CREATE INDEX idx_schemes_agency ON schemes(funding_agency);
CREATE INDEX idx_schemes_status ON schemes(status);
CREATE INDEX idx_schemes_deadline ON schemes(application_deadline);
CREATE INDEX idx_schemes_eligibility ON schemes USING gin(eligibility_criteria);
```

#### B2B Profile

```python
class B2BTier(str, Enum):
    T1_RAW_MATERIALS = "t1_raw_materials"
    T2_SERVICES = "t2_services"
    T3_TECH_API = "t3_tech_api"
    T4_CODEVELOPMENT = "t4_codevelopment"

class CollaborationIntent(str, Enum):
    SEEKING = "seeking"
    OFFERING = "offering"
    BOTH = "both"

@dataclass
class B2BProfile:
    profile_id: UUID
    startup_id: UUID
    tier: B2BTier
    intent: CollaborationIntent
    
    # For T1 - Raw Materials
    bom_items: Optional[List[BOMItem]]
    
    # For T2 - Services
    service_types: Optional[List[str]]
    service_scope: Optional[str]
    frequency: Optional[str]
    
    # For T3 - Tech/API
    tech_needs: Optional[List[str]]
    integration_requirements: Optional[str]
    data_volume: Optional[str]
    
    # For T4 - Co-development
    partnership_goals: Optional[str]
    ip_sharing_terms: Optional[str]
    resource_contributions: Optional[str]
    
    # Capacity constraints
    max_order_volume_monthly: Optional[int]
    min_order_quantity: Optional[int]
    lead_time_days: Optional[int]
    geographic_service_area: Optional[str]
    
    created_at: datetime
    updated_at: datetime

@dataclass
class BOMItem:
    item_name: str
    specification: str
    quantity_per_month: int
    unit_of_measure: str
    quality_standards: str
    price_range_min: Decimal
    price_range_max: Decimal
```

**PostgreSQL Schema**:
```sql
CREATE TABLE b2b_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    startup_id UUID NOT NULL REFERENCES startups(startup_id) ON DELETE CASCADE,
    tier VARCHAR(50) NOT NULL,
    intent VARCHAR(50) NOT NULL,
    bom_items JSONB,
    service_types TEXT[],
    service_scope TEXT,
    frequency VARCHAR(100),
    tech_needs TEXT[],
    integration_requirements TEXT,
    data_volume VARCHAR(100),
    partnership_goals TEXT,
    ip_sharing_terms TEXT,
    resource_contributions TEXT,
    max_order_volume_monthly INTEGER,
    min_order_quantity INTEGER,
    lead_time_days INTEGER,
    geographic_service_area VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_b2b_startup ON b2b_profiles(startup_id);
CREATE INDEX idx_b2b_tier ON b2b_profiles(tier);
CREATE INDEX idx_b2b_intent ON b2b_profiles(intent);
```

#### Investor Entity

```python
class InvestorType(str, Enum):
    ANGEL = "angel"
    VC = "vc"
    CORPORATE = "corporate"
    INSTITUTION = "institution"

class InvestorStatus(str, Enum):
    ACTIVELY_INVESTING = "actively_investing"
    SELECTIVE = "selective"
    NOT_INVESTING = "not_investing"

@dataclass
class Investor:
    investor_id: UUID
    investor_name: str
    investor_type: InvestorType
    contact_email: str
    contact_phone: str
    portfolio_url: Optional[str]
    
    # Investment preferences
    min_ticket_size: Decimal
    max_ticket_size: Decimal
    preferred_stages: List[str]
    target_sectors: List[str]
    geographic_focus: List[str]
    investment_thesis: str
    
    # Portfolio metrics
    active_investments: int
    total_portfolio_value: Decimal
    notable_exits: int
    avg_hold_period_months: int
    
    # Evaluation criteria
    min_users: Optional[int]
    min_revenue: Optional[Decimal]
    
    # Status
    availability_status: InvestorStatus
    
    created_at: datetime
    updated_at: datetime
```



**PostgreSQL Schema**:
```sql
CREATE TABLE investors (
    investor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_name VARCHAR(255) NOT NULL,
    investor_type VARCHAR(50) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(20),
    portfolio_url TEXT,
    min_ticket_size DECIMAL(15, 2) NOT NULL,
    max_ticket_size DECIMAL(15, 2) NOT NULL,
    preferred_stages TEXT[] NOT NULL,
    target_sectors TEXT[] NOT NULL,
    geographic_focus TEXT[],
    investment_thesis TEXT,
    active_investments INTEGER DEFAULT 0,
    total_portfolio_value DECIMAL(18, 2) DEFAULT 0,
    notable_exits INTEGER DEFAULT 0,
    avg_hold_period_months INTEGER,
    min_users INTEGER,
    min_revenue DECIMAL(15, 2),
    availability_status VARCHAR(50) DEFAULT 'actively_investing',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_ticket_range CHECK (min_ticket_size <= max_ticket_size),
    CONSTRAINT positive_ticket CHECK (min_ticket_size > 0)
);

CREATE INDEX idx_investors_type ON investors(investor_type);
CREATE INDEX idx_investors_status ON investors(availability_status);
CREATE INDEX idx_investors_sectors ON investors USING gin(target_sectors);
```

### Graph Storage for B2B Matching

**Bipartite Graph Adjacency List**:
```sql
CREATE TABLE b2b_graph_nodes (
    node_id UUID PRIMARY KEY,
    node_type VARCHAR(50) NOT NULL,  -- 'demand' or 'supply'
    startup_id UUID NOT NULL REFERENCES startups(startup_id),
    b2b_profile_id UUID NOT NULL REFERENCES b2b_profiles(profile_id),
    tier VARCHAR(50) NOT NULL,
    attributes JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE b2b_graph_edges (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_node_id UUID NOT NULL REFERENCES b2b_graph_nodes(node_id),
    supply_node_id UUID NOT NULL REFERENCES b2b_graph_nodes(node_id),
    edge_weight DECIMAL(5, 2) NOT NULL,  -- 0-100 match quality score
    spec_similarity DECIMAL(5, 2),
    price_compatibility DECIMAL(5, 2),
    capacity_alignment DECIMAL(5, 2),
    geographic_proximity DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_weight CHECK (edge_weight >= 0 AND edge_weight <= 100),
    UNIQUE(demand_node_id, supply_node_id)
);

CREATE INDEX idx_edges_demand ON b2b_graph_edges(demand_node_id);
CREATE INDEX idx_edges_supply ON b2b_graph_edges(supply_node_id);
CREATE INDEX idx_edges_weight ON b2b_graph_edges(edge_weight DESC);
```

### Embeddings Storage with pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE scheme_embeddings (
    scheme_id UUID PRIMARY KEY REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    description_embedding vector(768),  -- IndicBERT embedding dimension
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE startup_domain_embeddings (
    startup_id UUID PRIMARY KEY REFERENCES startups(startup_id) ON DELETE CASCADE,
    domain_description TEXT NOT NULL,
    domain_embedding vector(768),
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector similarity search index (IVFFlat for large datasets)
CREATE INDEX idx_scheme_embeddings ON scheme_embeddings 
    USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_startup_embeddings ON startup_domain_embeddings 
    USING ivfflat (domain_embedding vector_cosine_ops) WITH (lists = 100);
```


## API Design

### REST API Structure

The platform exposes a RESTful API organized by domain:

```
/api/v1
├── /auth
│   ├── POST /register
│   ├── POST /login
│   └── POST /refresh
├── /profiles
│   ├── GET /profiles/{founder_id}
│   ├── PUT /profiles/{founder_id}
│   ├── POST /profiles/{founder_id}/documents
│   └── GET /profiles/{founder_id}/completeness
├── /startups
│   ├── POST /startups
│   ├── GET /startups/{startup_id}
│   ├── PUT /startups/{startup_id}
│   └── POST /startups/{startup_id}/verify
├── /ideation
│   ├── POST /ideation/ideas
│   ├── GET /ideation/ideas/{idea_id}
│   └── POST /ideation/ideas/{idea_id}/roadmap
├── /schemes
│   ├── GET /schemes
│   ├── GET /schemes/{scheme_id}
│   ├── POST /schemes/eligibility
│   └── POST /schemes/applications
├── /b2b
│   ├── POST /b2b/profiles
│   ├── GET /b2b/profiles/{profile_id}
│   ├── POST /b2b/matches
│   └── POST /b2b/collaborations
├── /funding
│   ├── POST /funding/readiness
│   ├── GET /funding/readiness/{startup_id}
│   ├── POST /funding/investors/match
│   └── POST /funding/pipeline
└── /chat
    ├── POST /chat/message
    └── GET /chat/history/{session_id}
```

### Key API Endpoints

#### Scheme Eligibility Check

```python
@app.post("/api/v1/schemes/eligibility")
async def check_scheme_eligibility(
    startup_id: UUID,
    scheme_ids: Optional[List[UUID]] = None
) -> SchemeEligibilityResponse:
    """
    Check scheme eligibility using CP-SAT constraint solver.
    
    Request:
    {
        "startup_id": "uuid",
        "scheme_ids": ["uuid1", "uuid2"]  // Optional, check all if omitted
    }
    
    Response:
    {
        "eligible_schemes": [
            {
                "scheme_id": "uuid",
                "scheme_name": "SISFS",
                "relevance_score": 85.5,
                "matched_criteria": ["age", "stage", "domain"],
                "funding_amount": "20-50 lakhs"
            }
        ],
        "ineligible_schemes": [
            {
                "scheme_id": "uuid",
                "scheme_name": "Stand-Up India",
                "violated_constraints": ["gender", "entity_type"],
                "reason": "Scheme requires female founder and registered entity"
            }
        ],
        "total_checked": 45,
        "computation_time_ms": 150
    }
    """
    # Fetch startup profile
    startup = await db.get_startup(startup_id)
    founder = await db.get_founder(startup.founder_id)
    
    # Get schemes to check
    if scheme_ids:
        schemes = await db.get_schemes_by_ids(scheme_ids)
    else:
        schemes = await db.get_all_active_schemes()
    
    # Create CP-SAT model
    cpsat = CPSATBoundary()
    model = cpsat.create_model("scheme_eligibility")
    
    # Add decision variables and constraints
    eligible_vars = {}
    for scheme in schemes:
        var = cpsat.add_bool_var(model, f"eligible_{scheme.scheme_id}")
        eligible_vars[scheme.scheme_id] = var
        
        # Add eligibility constraints
        add_scheme_constraints(model, cpsat, scheme, startup, founder, var)
    
    # Solve
    result = cpsat.solve(model)
    
    # Process results
    eligible = []
    ineligible = []
    for scheme in schemes:
        if result.get_value(eligible_vars[scheme.scheme_id]):
            eligible.append(await format_eligible_scheme(scheme, startup))
        else:
            violated = await identify_violated_constraints(scheme, startup, founder)
            ineligible.append({
                "scheme_id": scheme.scheme_id,
                "scheme_name": scheme.scheme_name,
                "violated_constraints": violated,
                "reason": generate_reason(violated, scheme)
            })
    
    return SchemeEligibilityResponse(
        eligible_schemes=eligible,
        ineligible_schemes=ineligible,
        total_checked=len(schemes),
        computation_time_ms=result.solver_time_ms
    )
```

#### B2B Match Request

```python
@app.post("/api/v1/b2b/matches")
async def find_b2b_matches(
    profile_id: UUID,
    filters: Optional[B2BFilters] = None
) -> B2BMatchResponse:
    """
    Find B2B collaboration matches using graph matching + CP-SAT optimization.
    
    Request:
    {
        "profile_id": "uuid",
        "filters": {
            "min_match_score": 70,
            "max_distance_km": 500,
            "preferred_states": ["Tamil Nadu"],
            "min_trust_score": 60
        }
    }
    
    Response:
    {
        "matches": [
            {
                "partner_id": "uuid",
                "partner_name": "ABC Manufacturing",
                "match_score": 87.5,
                "spec_similarity": 0.92,
                "price_compatibility": 85.0,
                "capacity_available": 5000,
                "trust_score": 78,
                "location": "Chennai, Tamil Nadu",
                "distance_km": 45
            }
        ],
        "total_candidates": 150,
        "matched_count": 12,
        "computation_time_ms": 230
    }
    """
    # Get B2B profile
    profile = await db.get_b2b_profile(profile_id)
    startup = await db.get_startup(profile.startup_id)
    
    # Get graph engine
    graph_engine = GraphEngine()
    await graph_engine.load_graph(db)
    
    # Find candidate matches from graph
    if profile.intent in ["seeking", "both"]:
        # This is a demand node, find supply matches
        candidates = graph_engine.get_top_k_matches(
            node_id=str(profile_id),
            k=min(filters.max_results or 50, 100)
        )
    else:
        # This is a supply node, find demand matches
        candidates = graph_engine.get_reverse_matches(
            node_id=str(profile_id),
            k=min(filters.max_results or 50, 100)
        )
    
    # Filter by minimum score
    min_score = filters.min_match_score or 70
    candidates = [(node_id, score) for node_id, score in candidates 
                  if score >= min_score]
    
    # Apply CP-SAT constraints for feasible allocation
    cpsat = CPSATBoundary()
    model = cpsat.create_model("b2b_matching")
    
    # Add capacity and compatibility constraints
    feasible_matches = []
    for node_id, graph_score in candidates:
        partner_profile = await db.get_b2b_profile(UUID(node_id))
        partner_startup = await db.get_startup(partner_profile.startup_id)
        
        # Check hard constraints (capacity, price, distance)
        if await check_b2b_constraints(profile, partner_profile, filters):
            trust_score = await calculate_trust_score(partner_startup.startup_id)
            
            if trust_score >= (filters.min_trust_score or 0):
                feasible_matches.append({
                    "partner_id": partner_startup.startup_id,
                    "partner_name": partner_startup.startup_name,
                    "match_score": graph_score,
                    "trust_score": trust_score,
                    "location": f"{partner_startup.location}",
                    "distance_km": calculate_distance(startup.location, partner_startup.location),
                    "capacity_available": partner_profile.max_order_volume_monthly
                })
    
    # Sort by match score
    feasible_matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    return B2BMatchResponse(
        matches=feasible_matches,
        total_candidates=len(candidates),
        matched_count=len(feasible_matches),
        computation_time_ms=compute_time()
    )
```

#### Funding Readiness Assessment

```python
@app.post("/api/v1/funding/readiness")
async def assess_funding_readiness(
    startup_id: UUID
) -> FundingReadinessResponse:
    """
    Assess funding readiness across 6 dimensions.
    
    Response:
    {
        "overall_score": 68,
        "readiness_category": "ready",
        "dimension_scores": {
            "team_strength": 72,
            "product_maturity": 65,
            "market_traction": 70,
            "financial_health": 58,
            "pitch_quality": 75,
            "legal_compliance": 90
        },
        "gap_areas": [
            {
                "dimension": "financial_health",
                "current_score": 58,
                "target_score": 70,
                "recommendations": [
                    {
                        "action": "Extend runway through cost optimization",
                        "impact": "high",
                        "effort": "medium",
                        "expected_improvement": 8
                    }
                ]
            }
        ],
        "assessment_date": "2024-01-15T10:30:00Z"
    }
    """
    # Fetch startup data
    startup = await db.get_startup(startup_id)
    founder = await db.get_founder(startup.founder_id)
    
    # Initialize Funding Swarm
    funding_swarm = FundingSwarm()
    
    # Assess each dimension in parallel
    assessments = await asyncio.gather(
        funding_swarm.assess_team_strength(startup, founder),
        funding_swarm.assess_product_maturity(startup),
        funding_swarm.assess_market_traction(startup),
        funding_swarm.assess_financial_health(startup),
        funding_swarm.assess_pitch_quality(startup),
        funding_swarm.assess_legal_compliance(startup)
    )
    
    dimension_scores = {
        "team_strength": assessments[0].score,
        "product_maturity": assessments[1].score,
        "market_traction": assessments[2].score,
        "financial_health": assessments[3].score,
        "pitch_quality": assessments[4].score,
        "legal_compliance": assessments[5].score
    }
    
    # Compute weighted overall score
    weights = {
        "team_strength": 0.20,
        "product_maturity": 0.20,
        "market_traction": 0.25,
        "financial_health": 0.15,
        "pitch_quality": 0.10,
        "legal_compliance": 0.10
    }
    
    overall_score = sum(dimension_scores[dim] * weights[dim] 
                       for dim in dimension_scores)
    
    # Classify readiness
    if overall_score < 40:
        category = "not_ready"
    elif overall_score < 60:
        category = "developing"
    elif overall_score < 80:
        category = "ready"
    else:
        category = "highly_ready"
    
    # Generate gap analysis and recommendations
    gap_areas = []
    for dim, score in dimension_scores.items():
        if score < 60:
            recommendations = await funding_swarm.generate_recommendations(
                dimension=dim,
                current_score=score,
                startup=startup
            )
            gap_areas.append({
                "dimension": dim,
                "current_score": score,
                "target_score": 70,
                "recommendations": recommendations
            })
    
    return FundingReadinessResponse(
        overall_score=round(overall_score),
        readiness_category=category,
        dimension_scores=dimension_scores,
        gap_areas=gap_areas,
        assessment_date=datetime.utcnow()
    )
```



## Error Handling

### Error Classification and Response Strategy

The platform implements a hierarchical error handling strategy with specific error types and recovery mechanisms:

#### Error Categories

**1. Client Errors (4xx)**
- `400 Bad Request`: Invalid input, validation failures
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Valid token but insufficient permissions
- `404 Not Found`: Resource does not exist
- `409 Conflict`: State conflict (e.g., duplicate entity)
- `422 Unprocessable Entity`: Semantic validation failures
- `429 Too Many Requests`: Rate limit exceeded

**2. Server Errors (5xx)**
- `500 Internal Server Error`: Unhandled exceptions
- `502 Bad Gateway`: External service (MCA21, DPIIT) failure
- `503 Service Unavailable`: System overload or maintenance
- `504 Gateway Timeout`: External service timeout

**3. Domain-Specific Errors**
- `CPSAT_INFEASIBLE`: Constraint model has no feasible solution
- `CPSAT_TIMEOUT`: Solver exceeded time limit
- `TRANSLATION_FAILED`: Translation service error with fallback
- `OCR_LOW_CONFIDENCE`: Document text extraction unreliable
- `GRAPH_UPDATE_FAILED`: Bipartite graph inconsistency

### Error Response Format

```python
@dataclass
class ErrorResponse:
    """Standardized error response format"""
    error_code: str  # Machine-readable code
    error_message: str  # Human-readable message
    error_details: Optional[Dict[str, Any]]  # Additional context
    timestamp: datetime
    request_id: str  # For tracing
    suggestions: Optional[List[str]]  # Recovery suggestions

# Example error responses:

# Validation Error
{
    "error_code": "VALIDATION_FAILED",
    "error_message": "Profile validation failed",
    "error_details": {
        "field": "date_of_birth",
        "constraint": "must be at least 18 years old",
        "provided_value": "2010-05-15"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123",
    "suggestions": [
        "Ensure date of birth indicates age 18 or above",
        "Use format YYYY-MM-DD"
    ]
}

# CP-SAT Infeasibility
{
    "error_code": "NO_ELIGIBLE_SCHEMES",
    "error_message": "No schemes match your current profile",
    "error_details": {
        "total_schemes_checked": 45,
        "most_common_violations": [
            {"constraint": "entity_type", "count": 28},
            {"constraint": "revenue_range", "count": 12}
        ]
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_xyz789",
    "suggestions": [
        "Register your entity (required for 28 schemes)",
        "Improve profile completeness to 80%+ to unlock more schemes",
        "Consider schemes requiring lower revenue thresholds"
    ]
}
```

### Exception Handling in Swarms

Each agent swarm implements graceful degradation:

```python
class ProfileSwarm:
    async def process_document(self, document: Document) -> DocumentResult:
        """Process document with fallback strategies"""
        try:
            # Primary: Cloud OCR service (high accuracy)
            ocr_result = await cloud_ocr_service.extract_text(document)
            
            if ocr_result.confidence < 0.8:
                logger.warning(f"Low OCR confidence: {ocr_result.confidence}")
                # Fallback: Local OCR
                ocr_result = await local_ocr_service.extract_text(document)
            
            return DocumentResult(
                extracted_data=ocr_result.data,
                confidence=ocr_result.confidence,
                status="success"
            )
            
        except CloudOCRTimeoutError:
            # Fallback: Local OCR immediately
            logger.error("Cloud OCR timeout, using local fallback")
            ocr_result = await local_ocr_service.extract_text(document)
            return DocumentResult(
                extracted_data=ocr_result.data,
                confidence=ocr_result.confidence,
                status="fallback_used",
                warning="Cloud service unavailable"
            )
            
        except OCRExtractionError as e:
            # Manual review required
            logger.error(f"OCR extraction failed: {e}")
            await db.mark_document_for_manual_review(document.document_id)
            raise DocumentProcessingError(
                "Unable to extract text from document",
                suggestions=[
                    "Ensure document is clear and legible",
                    "Try uploading a higher quality image",
                    "Document marked for manual review"
                ]
            )
```

### Retry Logic with Exponential Backoff

```python
async def call_external_api_with_retry(
    api_func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Any:
    """
    Retry external API calls with exponential backoff.
    Used for: MCA21, DPIIT, GST validation APIs.
    """
    for attempt in range(max_retries):
        try:
            result = await api_func()
            return result
        except (TimeoutError, ConnectionError) as e:
            if attempt == max_retries - 1:
                raise ExternalServiceError(
                    f"Failed after {max_retries} attempts: {str(e)}"
                )
            
            # Exponential backoff: 1s, 2s, 4s, ...
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s")
            await asyncio.sleep(delay)
```

### Circuit Breaker Pattern for External Services

```python
class CircuitBreaker:
    """Prevent cascading failures from external service outages"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable) -> Any:
        if self.state == "OPEN":
            # Check if timeout period has passed
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError(
                    "Service temporarily unavailable due to repeated failures"
                )
        
        try:
            result = await func()
            # Success: reset failure count
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
            self.failure_count = 0
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e

# Usage:
mca21_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

async def validate_cin(cin_number: str) -> bool:
    return await mca21_circuit_breaker.call(
        lambda: mca21_api.validate(cin_number)
    )
```


## Correctness Properties

### Constraint Programming Correctness Guarantees

The CP-SAT boundary provides mathematical guarantees that ensure all recommendations are valid:

**Property 1: Scheme Eligibility Soundness**
- **Statement**: If a scheme is returned as "eligible", the startup satisfies ALL eligibility constraints.
- **Guarantee**: CP-SAT solver guarantees feasibility. No false positives.
- **Verification**: Unit tests with known eligible/ineligible profiles, constraint violation logs.

**Property 2: Scheme Eligibility Completeness**
- **Statement**: If a scheme is NOT returned, there exists at least one violated constraint.
- **Guarantee**: Infeasibility analysis identifies violated constraints via IIS (Irreducible Infeasible Subset).
- **Verification**: For each ineligible scheme, verify at least one constraint is violated.

**Property 3: B2B Matching Optimality**
- **Statement**: The returned B2B matches maximize total match quality subject to capacity constraints.
- **Guarantee**: NetworkX maximum weight matching finds globally optimal assignment.
- **Verification**: Compare objective value with brute-force search on small test cases.

**Property 4: Investor Matching Consistency**
- **Statement**: If an investor is returned as a match, all hard constraints are satisfied.
- **Guarantee**: CP-SAT constraint satisfaction ensures no constraint violations.
- **Verification**: Post-solution validation checks all constraints explicitly.

### Data Integrity Invariants

**Invariant 1: Profile Completeness Score Consistency**
```python
def verify_completeness_score(profile: FounderProfile) -> bool:
    """Verify computed completeness score matches actual data"""
    expected_score = compute_completeness_score(profile)
    return profile.completeness_score == expected_score
```

**Invariant 2: Trust Score Bounds**
```python
def verify_trust_score(trust_score: float) -> bool:
    """Trust scores must be in [0, 100]"""
    return 0 <= trust_score <= 100
```

**Invariant 3: Graph Bipartiteness**
```python
def verify_bipartite_graph(graph: nx.Graph) -> bool:
    """B2B graph must be bipartite with no edges within same partition"""
    demand_nodes = {n for n, d in graph.nodes(data=True) if d['bipartite'] == 0}
    supply_nodes = {n for n, d in graph.nodes(data=True) if d['bipartite'] == 1}
    
    for u, v in graph.edges():
        if (u in demand_nodes and v in demand_nodes) or \
           (u in supply_nodes and v in supply_nodes):
            return False  # Invalid: edge within same partition
    return True
```

**Invariant 4: Referential Integrity**
- All `startup_id` foreign keys reference existing founders
- All `scheme_id` foreign keys in applications reference active schemes
- Enforced by PostgreSQL foreign key constraints + application-level checks

### Idempotency Guarantees

**Idempotent Operations**:
- `PUT /profiles/{id}`: Updating profile with same data yields same state
- `POST /schemes/eligibility`: Running eligibility check multiple times with same profile returns identical results (deterministic)
- `POST /b2b/matches`: Graph-based matching is deterministic given same graph state

**Non-Idempotent Operations** (with safeguards):
- `POST /schemes/applications`: Creates new application unless duplicate check detects existing application
- `POST /b2b/collaborations`: Creates new collaboration with unique UUID

### Transactional Guarantees

**ACID Properties**:
- **Atomicity**: All database operations wrapped in transactions; rollback on failure
- **Consistency**: Foreign key constraints, check constraints enforce data validity
- **Isolation**: Read Committed isolation level (PostgreSQL default)
- **Durability**: WAL (Write-Ahead Logging) ensures persistence

**Example Transaction**:
```python
async def create_startup_with_verification(startup_data: Dict) -> Startup:
    async with db.transaction():
        # Step 1: Create startup record
        startup = await db.insert_startup(startup_data)
        
        # Step 2: Validate legal entities
        validation_result = await legal_validator.validate(
            cin=startup_data.get('cin_number'),
            dpiit=startup_data.get('dpiit_number')
        )
        
        if not validation_result.success:
            raise ValidationError("Legal entity validation failed")
        
        # Step 3: Update verification status
        await db.update_startup_verification(
            startup.startup_id,
            status="verified",
            validated_at=datetime.utcnow()
        )
        
        # Step 4: Create B2B graph node if applicable
        if startup_data.get('b2b_profile'):
            await graph_engine.add_startup_node(startup)
        
        return startup
    # Transaction commits automatically if no exception raised
    # Rollback automatic on exception
```


## Testing Strategy

### Unit Testing

**Coverage Target**: 80%+ code coverage for core business logic

**Key Test Suites**:

1. **CP-SAT Constraint Tests**
```python
def test_scheme_eligibility_age_constraint():
    """Test age constraint enforcement"""
    founder = FounderProfile(age=25, ...)
    scheme = Scheme(min_age=18, max_age=35, ...)
    
    cpsat = CPSATBoundary()
    model = cpsat.create_model("test")
    eligible = cpsat.add_bool_var(model, "eligible")
    
    add_age_constraint(model, cpsat, scheme, founder, eligible)
    result = cpsat.solve(model)
    
    assert result.get_value(eligible) == True
    
def test_scheme_eligibility_age_violation():
    """Test age constraint violation"""
    founder = FounderProfile(age=40, ...)
    scheme = Scheme(min_age=18, max_age=35, ...)
    
    cpsat = CPSATBoundary()
    model = cpsat.create_model("test")
    eligible = cpsat.add_bool_var(model, "eligible")
    
    add_age_constraint(model, cpsat, scheme, founder, eligible)
    result = cpsat.solve(model)
    
    assert result.get_value(eligible) == False
```

2. **Graph Matching Tests**
```python
def test_bipartite_graph_construction():
    """Test bipartite graph node and edge creation"""
    graph_engine = GraphEngine()
    
    demand_id = "demand_1"
    supply_id = "supply_1"
    
    graph_engine.add_demand_node(demand_id, {...})
    graph_engine.add_supply_node(supply_id, {...})
    graph_engine.add_edge(demand_id, supply_id, weight=85.0)
    
    assert graph_engine.graph.number_of_nodes() == 2
    assert graph_engine.graph.number_of_edges() == 1
    assert verify_bipartite_graph(graph_engine.graph) == True

def test_edge_weight_computation():
    """Test match quality score calculation"""
    demand = {"specification": "PCB manufacturing", "budget": 10000, ...}
    supply = {"offering": "PCB production services", "price": 9000, ...}
    
    graph_engine = GraphEngine()
    weight = graph_engine.compute_edge_weight(demand, supply)
    
    assert 0 <= weight <= 100
    assert weight > 70  # High similarity expected
```

3. **Embedding Service Tests**
```python
def test_embedding_generation():
    """Test IndicBERT embedding generation"""
    service = EmbeddingService()
    text = "AI-based healthcare startup"
    
    embedding = service.embed(text, language="en")
    
    assert embedding.shape == (768,)
    assert not np.isnan(embedding).any()

def test_cosine_similarity():
    """Test similarity calculation"""
    service = EmbeddingService()
    emb1 = service.embed("healthcare AI startup")
    emb2 = service.embed("medical technology company")
    emb3 = service.embed("food delivery platform")
    
    sim_high = service.cosine_similarity(emb1, emb2)
    sim_low = service.cosine_similarity(emb1, emb3)
    
    assert sim_high > sim_low
    assert sim_high > 0.7
```

### Integration Testing

**Test External Service Integrations**:

```python
@pytest.mark.integration
async def test_mca21_validation():
    """Test MCA21 API integration for CIN validation"""
    legal_validator = LegalValidator()
    
    # Valid CIN
    result = await legal_validator.validate_cin("U72900TN2020PTC123456")
    assert result.is_valid == True
    assert result.company_name is not None
    
    # Invalid CIN
    result = await legal_validator.validate_cin("INVALID123")
    assert result.is_valid == False

@pytest.mark.integration
async def test_end_to_end_scheme_matching():
    """Test complete scheme matching workflow"""
    # Create test founder and startup
    founder = await db.create_founder({...})
    startup = await db.create_startup({...})
    
    # Call API
    response = await client.post(
        "/api/v1/schemes/eligibility",
        json={"startup_id": str(startup.startup_id)}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "eligible_schemes" in data
    assert "ineligible_schemes" in data
    assert data["total_checked"] > 0
```

### Property-Based Testing

**Use Hypothesis for constraint verification**:

```python
from hypothesis import given, strategies as st

@given(
    age=st.integers(min_value=18, max_value=100),
    revenue=st.decimals(min_value=0, max_value=10000000),
    employees=st.integers(min_value=1, max_value=1000)
)
def test_scheme_eligibility_properties(age, revenue, employees):
    """Property: eligible schemes satisfy all constraints"""
    founder = FounderProfile(age=age, ...)
    startup = StartupProfile(monthly_revenue=revenue, employee_count=employees, ...)
    
    eligible_schemes = get_eligible_schemes(founder, startup)
    
    for scheme in eligible_schemes:
        # Property: age within range
        assert scheme.min_age <= age <= scheme.max_age
        # Property: revenue within range
        assert scheme.min_revenue <= revenue <= scheme.max_revenue
```

### Performance Testing

**Load Testing with Locust**:

```python
from locust import HttpUser, task, between

class StartupOSUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def check_scheme_eligibility(self):
        self.client.post("/api/v1/schemes/eligibility", json={
            "startup_id": "test-uuid"
        })
    
    @task(2)
    def find_b2b_matches(self):
        self.client.post("/api/v1/b2b/matches", json={
            "profile_id": "test-uuid"
        })
    
    @task(1)
    def assess_funding_readiness(self):
        self.client.post("/api/v1/funding/readiness", json={
            "startup_id": "test-uuid"
        })

# Performance targets:
# - 95th percentile response time < 500ms for eligibility checks
# - 95th percentile response time < 1000ms for B2B matching
# - Throughput: 1000 requests/second
```

### Security Testing

**OWASP Top 10 Verification**:

1. **SQL Injection Prevention**: Use parameterized queries (SQLAlchemy ORM)
2. **XSS Prevention**: Sanitize all user inputs, CSP headers
3. **Authentication**: JWT with refresh tokens, secure password hashing (bcrypt)
4. **Authorization**: Role-based access control (RBAC)
5. **Sensitive Data**: Encryption at rest (AES-256), TLS 1.3 in transit
6. **Rate Limiting**: 100 requests/minute per user, 1000/minute globally

```python
@pytest.mark.security
def test_sql_injection_prevention():
    """Verify SQL injection is prevented"""
    malicious_input = "'; DROP TABLE founders; --"
    
    response = client.get(f"/api/v1/profiles/search?name={malicious_input}")
    
    # Should not execute malicious SQL
    assert founders_table_exists() == True
    assert response.status_code in [200, 400]  # Either safe handling or validation error
```

---

This comprehensive design document provides an industrial-grade technical specification for Tamil Nadu StartupOS (Vanigam), covering architecture, components, APIs, data models, error handling, correctness properties, and testing strategies suitable for a professional development team to implement.
