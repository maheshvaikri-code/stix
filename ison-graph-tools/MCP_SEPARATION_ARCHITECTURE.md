# ISONGraph MCP Servers - Separation of Concerns

## Core Foundation: ISON & ISONGraph

```
┌─────────────────────────────────────────────────────────────────┐
│                         ISON FORMAT                             │
│  Token-efficient data notation (72% savings vs JSON)            │
│  Native format for LLM context injection                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ISONGraph                               │
│  Lightweight, production-ready graph store built on ISON        │
│  - Native ISON storage (no conversion overhead)                 │
│  - ISONQL query language                                        │
│  - Schema validation                                            │
│  - Optimized for AI/LLM workloads                              │
│  - Competitor to Neo4j (but token-efficient!)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ALL TOOLS BUILT ON ISONGRAPH                 │
│  Memory │ Governance │ Learning │ Compliance │ Cache │ etc.    │
└─────────────────────────────────────────────────────────────────┘
```

## Complete MCP Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Agents                                       │
│     Claude  │  GPT-4  │  Gemini  │  Custom Agents  │  Agent Swarms          │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ MCP Protocol
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LAYER 1: Domain Services                            │
│                                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   Memory    │ │ Governance  │ │  Learning   │ │ Compliance  │          │
│  │    MCP      │ │    MCP      │ │    MCP      │ │    MCP      │          │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘          │
│         │               │               │               │                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                          │
│  │  Code Flow  │ │  Converter  │ │   Schema    │                          │
│  │    MCP      │ │    MCP      │ │    MCP      │                          │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                          │
└─────────┼───────────────┼───────────────┼───────────────────────────────────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LAYER 2: Core Services                                │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      ISONCache MCP                                     │ │
│  │  - Token budget management across agents                              │ │
│  │  - ISON-formatted responses (72% token savings)                       │ │
│  │  - Graph subgraph caching                                             │ │
│  │  - Embedding storage for semantic search                              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      ISONGraph MCP                                     │ │
│  │  - Core graph operations (CRUD)                                       │ │
│  │  - ISONQL query execution                                             │ │
│  │  - Schema validation & enforcement                                    │ │
│  │  - Graph persistence & loading                                        │ │
│  │  - Index management                                                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 3: Storage                                     │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │    File     │  │   SQLite    │  │   Redis     │  │ PostgreSQL  │       │
│  │   (.ison)   │  │  (indexed)  │  │  (cluster)  │  │  (metadata) │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                                             │
│  All storage uses ISON format natively - no conversion overhead            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Why ISONGraph as Foundation (vs Neo4j)

| Aspect | ISONGraph | Neo4j |
|--------|-----------|-------|
| **Token Efficiency** | Native ISON (72% savings) | Requires conversion |
| **LLM Optimized** | Built for AI context | General purpose |
| **Format** | ISON (lightweight) | Custom binary |
| **Query Language** | ISONQL | Cypher |
| **Overhead** | Minimal | JVM, memory heavy |
| **Deployment** | Embedded or standalone | Server required |
| **Cost** | Open source | Enterprise licensing |

---

## MCP Server Specifications

### 1. ISONGraph MCP (Foundation)

```
┌─────────────────────────────────────────────────────────────┐
│                    ISONGraph MCP                            │
│              (Core Graph Store Service)                     │
│                                                             │
│  The foundation layer - all other tools depend on this      │
│                                                             │
│  Tools:                                                     │
│  ├── GRAPH MANAGEMENT                                      │
│  │   ├── graph_create          - Create new graph          │
│  │   ├── graph_load            - Load from .ison file      │
│  │   ├── graph_save            - Save to .ison file        │
│  │   ├── graph_clone           - Clone a graph             │
│  │   ├── graph_merge           - Merge two graphs          │
│  │   ├── graph_stats           - Get statistics            │
│  │   └── graph_delete          - Delete graph              │
│  │                                                         │
│  ├── NODE OPERATIONS                                       │
│  │   ├── node_add              - Add node                  │
│  │   ├── node_get              - Get by type:id            │
│  │   ├── node_update           - Update properties         │
│  │   ├── node_delete           - Delete node               │
│  │   ├── node_find             - Find by properties        │
│  │   └── node_count            - Count by type             │
│  │                                                         │
│  ├── EDGE OPERATIONS                                       │
│  │   ├── edge_add              - Add relationship          │
│  │   ├── edge_get              - Get edge                  │
│  │   ├── edge_update           - Update properties         │
│  │   ├── edge_delete           - Delete edge               │
│  │   ├── edge_find             - Find edges                │
│  │   └── edge_count            - Count by type             │
│  │                                                         │
│  ├── ISONQL QUERIES                                        │
│  │   ├── query_execute         - Execute ISONQL query      │
│  │   ├── query_traverse        - TRAVERSE queries          │
│  │   ├── query_match           - MATCH patterns            │
│  │   ├── query_aggregate       - Aggregation queries       │
│  │   └── query_explain         - Explain query plan        │
│  │                                                         │
│  ├── SCHEMA                                                │
│  │   ├── schema_set            - Set graph schema          │
│  │   ├── schema_get            - Get current schema        │
│  │   ├── schema_validate       - Validate graph            │
│  │   └── schema_enforce        - Enable enforcement        │
│  │                                                         │
│  └── INDEXING                                              │
│      ├── index_create          - Create index              │
│      ├── index_drop            - Drop index                │
│      ├── index_list            - List indexes              │
│      └── index_rebuild         - Rebuild index             │
│                                                             │
│  Storage Backends:                                          │
│  - File (.ison) - Simple, portable                         │
│  - SQLite - Indexed, queryable                             │
│  - Redis - Distributed, fast                               │
│  - PostgreSQL - Metadata, full-text search                 │
│                                                             │
│  Why Separate:                                              │
│  - Foundation for ALL other tools                          │
│  - Graph operations need dedicated resources               │
│  - Different scaling characteristics                       │
│  - Persistence management                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2. ISONCache MCP (Token Management)

```
┌─────────────────────────────────────────────────────────────┐
│                    ISONCache MCP                            │
│              (Token-Efficient Caching)                      │
│                                                             │
│  Manages token budgets and caching for LLM context          │
│                                                             │
│  Tools:                                                     │
│  ├── BASIC CACHE                                           │
│  │   ├── cache_set             - Store (auto ISON format)  │
│  │   ├── cache_get             - Retrieve (token-efficient)│
│  │   ├── cache_delete          - Delete key                │
│  │   ├── cache_exists          - Check existence           │
│  │   └── cache_clear           - Clear namespace           │
│  │                                                         │
│  ├── TOKEN BUDGETS                                         │
│  │   ├── budget_create         - Create agent budget       │
│  │   ├── budget_allocate       - Allocate for purpose      │
│  │   ├── budget_remaining      - Check remaining           │
│  │   ├── budget_release        - Release allocation        │
│  │   └── budget_reset          - Reset to max              │
│  │                                                         │
│  ├── BUDGETED RETRIEVAL                                    │
│  │   ├── get_within_budget     - Get data within limit     │
│  │   ├── get_context_for_llm   - Optimized LLM context     │
│  │   ├── count_tokens          - Count tokens              │
│  │   └── estimate_tokens       - Estimate without fetch    │
│  │                                                         │
│  ├── GRAPH CACHING                                         │
│  │   ├── graph_cache_subgraph  - Cache graph subset        │
│  │   ├── graph_cache_traverse  - Cached traversal          │
│  │   └── graph_cache_invalidate- Invalidate on change      │
│  │                                                         │
│  ├── EMBEDDINGS                                            │
│  │   ├── embedding_store       - Store with vector         │
│  │   ├── embedding_search      - Similarity search         │
│  │   └── embedding_delete      - Remove embedding          │
│  │                                                         │
│  └── CROSS-AGENT                                           │
│      ├── share_cache           - Share between agents      │
│      ├── subscribe             - Subscribe to updates      │
│      └── broadcast             - Broadcast to subscribers  │
│                                                             │
│  Token Savings: 72% vs JSON                                │
│                                                             │
│  Why Separate:                                              │
│  - Central token coordination                              │
│  - Shared across ALL agents                                │
│  - Prevents token budget conflicts                         │
│  - Cache persistence across restarts                       │
└─────────────────────────────────────────────────────────────┘
```

### 3. Agent Memory MCP

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent Memory MCP                          │
│              (Persistent Agent Context)                     │
│                                                             │
│  12+ memory stores for coding agents                        │
│  Built on ISONGraph for graph-based memory                  │
│                                                             │
│  Tools:                                                     │
│  ├── INITIALIZATION                                        │
│  │   ├── memory_init           - Init for project          │
│  │   ├── memory_load           - Load saved memory         │
│  │   ├── memory_save           - Persist memory            │
│  │   └── memory_bootstrap      - Auto-scan project         │
│  │                                                         │
│  ├── CONTEXT                                               │
│  │   ├── context_get           - Get coding context        │
│  │   ├── context_for_task      - Task-specific context     │
│  │   └── context_for_files     - File-specific context     │
│  │                                                         │
│  ├── CONVENTIONS                                           │
│  │   ├── convention_add        - Add code convention       │
│  │   ├── convention_query      - Query conventions         │
│  │   └── convention_for_file   - Get for specific file     │
│  │                                                         │
│  ├── DECISIONS (ADRs)                                      │
│  │   ├── decision_add          - Record decision           │
│  │   ├── decision_query        - Query decisions           │
│  │   └── decision_related      - Find related decisions    │
│  │                                                         │
│  ├── BUG PATTERNS                                          │
│  │   ├── bug_pattern_add       - Record bug pattern        │
│  │   ├── bug_fix_add           - Add fix template          │
│  │   ├── bug_check             - Check for known bugs      │
│  │   └── bug_prevent           - Prevention advice         │
│  │                                                         │
│  ├── DEPENDENCIES                                          │
│  │   ├── dependency_add        - Track dependency          │
│  │   ├── dependency_quirk      - Record quirk/workaround   │
│  │   └── dependency_query      - Query dependencies        │
│  │                                                         │
│  ├── SESSIONS                                              │
│  │   ├── session_start         - Start coding session      │
│  │   ├── session_end           - End with summary          │
│  │   ├── session_handoff       - Get handoff context       │
│  │   └── session_history       - Session history           │
│  │                                                         │
│  ├── TEAM                                                  │
│  │   ├── team_add_expertise    - Record expertise          │
│  │   ├── team_who_knows        - Find expert               │
│  │   └── team_ownership        - Code ownership            │
│  │                                                         │
│  ├── TASKS                                                 │
│  │   ├── todo_add              - Add task                  │
│  │   ├── todo_update           - Update status             │
│  │   ├── todo_query            - Query tasks               │
│  │   └── goal_track            - Track goals               │
│  │                                                         │
│  └── SKILLS                                                │
│      ├── skill_record          - Record skill use          │
│      └── skill_progression     - Get progression           │
│                                                             │
│  Dependencies: ISONGraph MCP, ISONCache MCP                │
│                                                             │
│  Why Separate:                                              │
│  - Per-project isolation                                   │
│  - Different retention policies                            │
│  - Memory-intensive for large projects                     │
│  - Independent backup/restore                              │
└─────────────────────────────────────────────────────────────┘
```

### 4. Agent Governance MCP

```
┌─────────────────────────────────────────────────────────────┐
│                 Agent Governance MCP                        │
│           (Policy, Authority, Safety Control)               │
│                                                             │
│  15 governance domains - SECURITY CRITICAL                  │
│  Built on ISONGraph for audit trail                         │
│                                                             │
│  Tools:                                                     │
│  ├── AUTHORITY (Domain 1)                                  │
│  │   ├── agent_register        - Register agent            │
│  │   ├── human_register        - Register human overseer   │
│  │   ├── authority_grant       - Grant authority           │
│  │   ├── authority_revoke      - Revoke authority          │
│  │   ├── authority_check       - Check permissions         │
│  │   └── delegation_create     - Delegate authority        │
│  │                                                         │
│  ├── POLICY (Domain 2)                                     │
│  │   ├── policy_add            - Add policy                │
│  │   ├── policy_evaluate       - Evaluate context          │
│  │   ├── rule_add              - Add rule to policy        │
│  │   └── policy_list           - List all policies         │
│  │                                                         │
│  ├── ACTION CONTROL                                        │
│  │   ├── action_check          - Is action permitted?      │
│  │   ├── action_record         - Record action taken       │
│  │   └── action_deny           - Deny with reason          │
│  │                                                         │
│  ├── ESCALATION (Domain 6)                                 │
│  │   ├── escalation_trigger    - Trigger escalation        │
│  │   ├── escalation_resolve    - Human resolves            │
│  │   ├── escalation_pending    - List pending              │
│  │   └── reviewer_add          - Add human reviewer        │
│  │                                                         │
│  ├── RISK (Domain 5)                                       │
│  │   ├── risk_assess           - Assess risk posture       │
│  │   ├── threat_add            - Add threat                │
│  │   ├── control_add           - Add control               │
│  │   └── incident_report       - Report incident           │
│  │                                                         │
│  ├── COORDINATION (Domain 8)                               │
│  │   ├── group_create          - Create agent group        │
│  │   ├── role_assign           - Assign role               │
│  │   ├── protocol_add          - Add protocol              │
│  │   └── coordination_check    - Check authority           │
│  │                                                         │
│  ├── ETHICS (Domain 9)                                     │
│  │   ├── value_add             - Add core value            │
│  │   ├── principle_add         - Add ethical principle     │
│  │   ├── dilemma_resolve       - Resolve dilemma           │
│  │   └── alignment_score       - Calculate alignment       │
│  │                                                         │
│  └── AUDIT (Domain 4)                                      │
│      ├── audit_trail           - Get decision trail        │
│      ├── audit_export          - Export for compliance     │
│      └── audit_query           - Query audit log           │
│                                                             │
│  Dependencies: ISONGraph MCP, ISONCache MCP                │
│                                                             │
│  ⚠️  SECURITY CRITICAL:                                    │
│  - Must be isolated from governed agents                   │
│  - Audit trail cannot be modified                          │
│  - Required for SOC2, ISO27001 compliance                  │
│  - Separate network/access controls                        │
└─────────────────────────────────────────────────────────────┘
```

### 5. Agent Learning MCP

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent Learning MCP                        │
│              (Experience & Improvement)                     │
│                                                             │
│  Continuous learning system for AI agents                   │
│  Built on ISONGraph for experience graphs                   │
│                                                             │
│  Tools:                                                     │
│  ├── EXPERIENCE                                            │
│  │   ├── experience_record     - Record experience         │
│  │   ├── experience_query      - Query past experiences    │
│  │   ├── experience_similar    - Find similar              │
│  │   └── experience_replay     - Replay for learning       │
│  │                                                         │
│  ├── MISTAKES                                              │
│  │   ├── mistake_record        - Record mistake            │
│  │   ├── mistake_patterns      - Detect patterns           │
│  │   ├── mistake_query         - Query by category         │
│  │   └── mistake_prevent       - Prevention advice         │
│  │                                                         │
│  ├── SKILLS                                                │
│  │   ├── skill_record          - Record skill use          │
│  │   ├── skill_level           - Get current level         │
│  │   ├── skill_progression     - Progression history       │
│  │   └── skill_recommend       - Recommend practice        │
│  │                                                         │
│  ├── ATTENTION                                             │
│  │   ├── attention_record      - Record attention          │
│  │   ├── attention_analyze     - Analyze patterns          │
│  │   └── attention_improve     - Improvement tips          │
│  │                                                         │
│  ├── SUPERVISION                                           │
│  │   ├── supervision_record    - Record supervision        │
│  │   ├── supervision_feedback  - Record feedback           │
│  │   └── supervision_stats     - Get statistics            │
│  │                                                         │
│  └── RETRAINING                                            │
│      ├── needs_identify        - Identify needs            │
│      ├── curriculum_generate   - Generate curriculum       │
│      ├── curriculum_execute    - Execute training          │
│      └── progress_track        - Track progress            │
│                                                             │
│  Dependencies: ISONGraph MCP, ISONCache MCP                │
│                                                             │
│  Why Separate:                                              │
│  - Large experience data volumes                           │
│  - ML workloads may need GPU                               │
│  - Different compute profile                               │
│  - Long-term retention                                     │
└─────────────────────────────────────────────────────────────┘
```

### 6. Compliance MCP (Unified Regulatory)

```
┌─────────────────────────────────────────────────────────────┐
│                    Compliance MCP                           │
│           (Unified Regulatory Compliance)                   │
│                                                             │
│  GDPR + CCPA + HIPAA + EU AI Act + PII                     │
│  Built on ISONGraph for compliance graphs                   │
│                                                             │
│  Tools:                                                     │
│  ├── UNIFIED                                               │
│  │   ├── compliance_check      - Cross-regulation check    │
│  │   ├── subject_register      - Register data subject     │
│  │   ├── pii_access_grant      - Grant PII access          │
│  │   ├── action_record         - Record for audit          │
│  │   └── report_generate       - Compliance report         │
│  │                                                         │
│  ├── GDPR (EU)                                             │
│  │   ├── gdpr_processing       - Art. 30 ROPA             │
│  │   ├── gdpr_consent          - Art. 7 consent           │
│  │   ├── gdpr_rights           - Art. 15-22 rights        │
│  │   ├── gdpr_breach           - Art. 33-34 breach        │
│  │   ├── gdpr_dpia             - Art. 35 DPIA             │
│  │   └── gdpr_transfer         - Art. 44-49 transfer      │
│  │                                                         │
│  ├── CCPA (California)                                     │
│  │   ├── ccpa_consumer         - Register consumer        │
│  │   ├── ccpa_opt_out          - Do Not Sell/Share        │
│  │   ├── ccpa_rights           - Consumer rights          │
│  │   └── ccpa_disclosure       - Disclosure tracking      │
│  │                                                         │
│  ├── HIPAA (Medical)                                       │
│  │   ├── hipaa_phi_classify    - Classify PHI             │
│  │   ├── hipaa_access          - Authorize access         │
│  │   ├── hipaa_minimum         - Minimum necessary        │
│  │   ├── hipaa_consent         - Record consent           │
│  │   └── hipaa_breach          - Report breach            │
│  │                                                         │
│  ├── EU AI ACT                                             │
│  │   ├── euai_system           - Register AI system       │
│  │   ├── euai_risk             - Risk classification      │
│  │   ├── euai_prohibited       - Check prohibited         │
│  │   ├── euai_conformity       - Conformity assessment    │
│  │   └── euai_incident         - Incident reporting       │
│  │                                                         │
│  └── PII                                                   │
│      ├── pii_scan              - Scan for PII             │
│      ├── pii_classify          - Classify field           │
│      ├── pii_inventory         - Data inventory           │
│      └── pii_lineage           - Data lineage             │
│                                                             │
│  Dependencies: ISONGraph MCP, ISONCache MCP                │
│                                                             │
│  ⚠️  LEGAL CRITICAL:                                       │
│  - Data residency (EU data stays in EU)                    │
│  - Jurisdiction-specific instances                         │
│  - Audit trail required                                    │
│  - Cannot be bypassed                                      │
└─────────────────────────────────────────────────────────────┘
```

### 7. Code Flow MCP

```
┌─────────────────────────────────────────────────────────────┐
│                    Code Flow MCP                            │
│              (Code Structure Analysis)                      │
│                                                             │
│  Analyzes codebases and creates flow graphs                 │
│  Results stored in ISONGraph                                │
│                                                             │
│  Tools:                                                     │
│  ├── ANALYSIS                                              │
│  │   ├── analyze_local         - Analyze directory         │
│  │   ├── analyze_github        - Analyze GitHub repo       │
│  │   ├── analyze_incremental   - Incremental update        │
│  │   └── analyze_diff          - Analyze git diff          │
│  │                                                         │
│  ├── ISONQL QUERIES                                        │
│  │   ├── query_callers         - TRAVERSE <- CALLS         │
│  │   ├── query_callees         - TRAVERSE -> CALLS         │
│  │   ├── query_imports         - TRAVERSE -> IMPORTS       │
│  │   ├── query_inheritance     - TRAVERSE -> INHERITS      │
│  │   ├── query_dependencies    - Module dependencies       │
│  │   └── query_custom          - Custom ISONQL query       │
│  │                                                         │
│  ├── STRUCTURE                                             │
│  │   ├── get_modules           - List modules              │
│  │   ├── get_classes           - List classes              │
│  │   ├── get_functions         - List functions            │
│  │   ├── get_file_tree         - File structure            │
│  │   └── get_complexity        - Complexity metrics        │
│  │                                                         │
│  └── EXPORT                                                │
│      ├── export_dot            - Graphviz DOT              │
│      ├── export_mermaid        - Mermaid diagram           │
│      └── export_subgraph       - Subgraph for display      │
│                                                             │
│  Dependencies: ISONGraph MCP, ISONCache MCP                │
│                                                             │
│  Why Separate:                                              │
│  - CPU-intensive parsing                                   │
│  - Large memory for big codebases                          │
│  - Results cached for reuse                                │
│  - Language-specific parsers                               │
└─────────────────────────────────────────────────────────────┘
```

### 8. Converter MCP

```
┌─────────────────────────────────────────────────────────────┐
│                    Converter MCP                            │
│              (Format Transformation)                        │
│                                                             │
│  Convert ISONGraph to/from other formats                    │
│  Export for visualization and external systems              │
│                                                             │
│  Tools:                                                     │
│  ├── EXPORT TO                                             │
│  │   ├── to_graphml            - GraphML (Gephi, yEd)      │
│  │   ├── to_rdf_turtle         - RDF/Turtle               │
│  │   ├── to_rdf_ntriples       - N-Triples                │
│  │   ├── to_csv                - CSV (nodes, edges)        │
│  │   ├── to_cypher             - Neo4j Cypher*            │
│  │   ├── to_dot                - Graphviz DOT              │
│  │   └── to_json               - Standard JSON             │
│  │                                                         │
│  │   * For migration FROM Neo4j to ISONGraph               │
│  │                                                         │
│  ├── IMPORT FROM                                           │
│  │   ├── from_graphml          - Import GraphML            │
│  │   ├── from_rdf              - Import RDF                │
│  │   ├── from_csv              - Import CSV                │
│  │   ├── from_json             - Import JSON               │
│  │   └── from_cypher           - Import Cypher dump*       │
│  │                                                         │
│  │   * Migrate existing Neo4j data to ISONGraph            │
│  │                                                         │
│  └── RENDER                                                │
│      ├── render_svg            - Render to SVG             │
│      ├── render_png            - Render to PNG             │
│      └── render_pdf            - Render to PDF             │
│                                                             │
│  Dependencies: ISONGraph MCP                               │
│                                                             │
│  Why Separate:                                              │
│  - STATELESS - easy horizontal scaling                     │
│  - CPU-bound rendering                                     │
│  - External tool dependencies (Graphviz)                   │
│  - Migration tool for Neo4j users                          │
└─────────────────────────────────────────────────────────────┘
```

### 9. Schema MCP

```
┌─────────────────────────────────────────────────────────────┐
│                     Schema MCP                              │
│           (Schema Generation & Validation)                  │
│                                                             │
│  Generate and validate ISONGraph schemas                    │
│                                                             │
│  Tools:                                                     │
│  ├── GENERATION                                            │
│  │   ├── generate_from_data    - Infer from data           │
│  │   ├── generate_from_sample  - From samples              │
│  │   └── analyze_structure     - Analyze data structure    │
│  │                                                         │
│  ├── FORMATTING                                            │
│  │   ├── format_python         - Python code output        │
│  │   ├── format_typescript     - TypeScript output         │
│  │   ├── format_json_schema    - JSON Schema output        │
│  │   └── format_ison_schema    - ISON Schema format        │
│  │                                                         │
│  ├── VALIDATION                                            │
│  │   ├── validate_node         - Validate node             │
│  │   ├── validate_edge         - Validate edge             │
│  │   ├── validate_graph        - Validate entire graph     │
│  │   └── get_violations        - List violations           │
│  │                                                         │
│  └── EVOLUTION                                             │
│      ├── diff_schemas          - Compare schemas           │
│      ├── migrate_schema        - Generate migration        │
│      └── check_compatibility   - Backwards compatible?     │
│                                                             │
│  Dependencies: ISONGraph MCP                               │
│                                                             │
│  Why Separate:                                              │
│  - Lightweight utility                                     │
│  - Shared across all tools                                 │
│  - Schema versioning                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Interaction Flow with ISONQL

```
Agent Request: "What functions call authenticate()?"
         │
         ▼
┌─────────────────┐
│  Code Flow MCP  │
└────────┬────────┘
         │ 1. Check cache
         ▼
┌─────────────────┐
│  ISONCache MCP  │ ──── Cache miss
└────────┬────────┘
         │ 2. Query graph
         ▼
┌─────────────────┐
│  ISONGraph MCP  │
│                 │
│  ISONQL Query:  │
│  TRAVERSE       │
│    function:authenticate │
│    <- CALLS     │
│    <- function  │
│  RETURN caller.name, caller.file │
└────────┬────────┘
         │ 3. Cache result
         ▼
┌─────────────────┐
│  ISONCache MCP  │ ──── Store in ISON format
└────────┬────────┘
         │ 4. Return (72% fewer tokens)
         ▼
┌─────────────────┐
│  Code Flow MCP  │
└────────┬────────┘
         │
         ▼
      Agent receives token-efficient response
```

---

## Deployment Examples

### Development (Single Machine)

```json
{
  "mcpServers": {
    "isongraph": {
      "command": "python",
      "args": ["-m", "isongraph_mcp.server"],
      "env": {"STORAGE": "file", "DATA_DIR": "./data"}
    },
    "cache": {
      "command": "python",
      "args": ["-m", "ison_cache_mcp.server"]
    },
    "memory": {
      "command": "python",
      "args": ["-m", "agent_memory_mcp.server"]
    },
    "governance": {
      "command": "python",
      "args": ["-m", "agent_governance_mcp.server"]
    },
    "compliance": {
      "command": "python",
      "args": ["-m", "compliance_mcp.server"]
    },
    "codeflow": {
      "command": "python",
      "args": ["-m", "codeflow_mcp.server"]
    }
  }
}
```

### Production (Kubernetes)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: isongraph-mcp
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: isongraph
        image: isongraph/core-mcp:latest
        env:
        - name: STORAGE_BACKEND
          value: "sqlite"  # Or redis for distributed
        - name: DATA_PATH
          value: "/data/isongraph"
        volumeMounts:
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: governance-mcp
  namespace: security  # Isolated namespace
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: governance
        image: isongraph/governance-mcp:latest
        env:
        - name: ISONGRAPH_MCP_URL
          value: "http://isongraph-mcp:8000"
      # Security: No external network access
      securityContext:
        readOnlyRootFilesystem: true
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-mcp-eu
  labels:
    region: eu
spec:
  template:
    spec:
      nodeSelector:
        topology.kubernetes.io/region: eu-west-1  # EU data residency
      containers:
      - name: compliance
        image: isongraph/compliance-mcp:latest
```

---

## Summary: ISONGraph Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    ISON FORMAT                              │
│         (72% token savings - foundation of everything)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ISONGraph                                │
│      (Native graph store with ISONQL - your product)        │
│      (Lightweight, production-ready, LLM-optimized)         │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  ISONGraph MCP  │ │  ISONCache MCP  │ │   Domain MCPs   │
│  (Graph Ops)    │ │  (Token Mgmt)   │ │  (Memory, Gov,  │
│                 │ │                 │ │   Compliance)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

**ISONGraph is the competitor to Neo4j** - not a client of it. All tools are built on ISONGraph, using ISON format natively for maximum token efficiency.
