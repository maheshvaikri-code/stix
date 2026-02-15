# ISON Use Case Examples

Practical examples demonstrating ISON as the primary data interchange format for AI systems.

---

## Table of Contents

1. [LLM Prompt Engineering](#1-llm-prompt-engineering)
2. [RAG Pipelines](#2-rag-pipelines)
3. [Multi-Agent AI Systems](#3-multi-agent-ai-systems)
4. [Tool and Function Call Results](#4-tool-and-function-call-results)
5. [Database Query Outputs](#5-database-query-outputs)
6. [Knowledge Base Serialization](#6-knowledge-base-serialization)
7. [Agentic Workflows](#7-agentic-workflows)
8. [Multimodal AI Systems](#8-multimodal-ai-systems)

---

## 1. LLM Prompt Engineering

### Use Case: Structured Context in System Prompts

When building LLM applications, you often need to inject structured data into prompts—user profiles, permissions, configuration, domain knowledge.

### Example: Customer Support Bot Context

```
# Customer context for support conversation
object.customer
id name tier account_age_months support_priority
C-1001 "Sarah Chen" enterprise 36 high

# Customer's active subscriptions
table.subscriptions
id product status monthly_cost renewal_date
SUB-101 "Pro Analytics" active 299.00 2025-02-15
SUB-102 "Data Warehouse" active 599.00 2025-03-01
SUB-103 "API Access" suspended 99.00 null

# Recent support history
table.support_history
ticket_id date issue resolution satisfaction
T-5001 2025-01-10 "Login issues" resolved 5
T-5002 2025-01-15 "Slow queries" resolved 4
T-5003 2025-01-18 "Billing question" pending null

# Agent permissions for this conversation
object.permissions
can_issue_refund can_extend_trial can_escalate max_discount_percent
true true true 25
```

**System prompt usage:**
```
You are a customer support agent. Here is the customer context:

{ison_data}

The customer is an enterprise tier client with high priority. 
Handle their suspended API Access subscription with care.
```

---

### Example: Code Assistant Context

```
# Project configuration
object.project
name language framework version build_system
"web-dashboard" TypeScript React 18.2.0 Vite

# Key dependencies
table.dependencies
name version purpose
react 18.2.0 "UI framework"
tanstack-query 5.0.0 "Data fetching"
zustand 4.4.0 "State management"
tailwindcss 3.3.0 "Styling"
vitest 1.0.0 "Testing"

# Code conventions
object.conventions
naming_style indent component_style state_management
camelCase 2 "functional with hooks" zustand

# Current file context
object.current_file
path line_count last_modified
src/components/Dashboard.tsx 245 2025-01-20
```

---

## 2. RAG Pipelines

### Use Case: Retrieved Documents for Question Answering

RAG systems retrieve relevant chunks and pass them to the LLM. ISON packs more chunks in fewer tokens.

### Example: Technical Documentation RAG

```
# Query metadata
object.query
id text timestamp user_id
Q-7842 "How do I configure authentication in MAPLE agents?" 2025-01-20T14:32:00Z U-101

# Retrieved chunks ranked by relevance
table.retrieved_chunks
rank chunk_id doc_id content similarity
1 CHK-1842 :DOC-42 "MAPLE agents support three authentication modes: API key, OAuth 2.0, and mTLS. Configure via the auth block in agent.yaml..." 0.94
2 CHK-1291 :DOC-29 "For OAuth 2.0, set auth.type to 'oauth2' and provide client_id, client_secret, and token_url. Tokens refresh automatically..." 0.91
3 CHK-1103 :DOC-42 "API key authentication is simplest: set auth.type to 'api_key' and auth.key to your key value or environment variable reference..." 0.87
4 CHK-892 :DOC-15 "mTLS requires certificate paths: auth.cert_path and auth.key_path. The agent validates server certificates by default..." 0.82
5 CHK-2001 :DOC-51 "Authentication errors return code AUTH_FAILED with details in error.context. Common causes: expired tokens, invalid keys..." 0.78

# Source documents metadata
table.documents
id title path updated author
:DOC-42 "MAPLE Agent Configuration Guide" docs/config.md 2025-01-15 :U-201
:DOC-29 "OAuth 2.0 Integration" docs/oauth.md 2025-01-10 :U-202
:DOC-15 "Security Best Practices" docs/security.md 2025-01-12 :U-201
:DOC-51 "Troubleshooting Guide" docs/troubleshoot.md 2025-01-18 :U-203
```

---

### Example: Multi-Modal RAG (Images + Text)

```
# Retrieved content mixing text and images
table.retrieved_items
rank id type content source similarity
1 TXT-421 text "The architecture uses a hub-and-spoke model where the orchestrator distributes tasks..." arch-guide.md 0.93
2 IMG-89 image null diagrams/architecture.png 0.91
3 TXT-422 text "Each spoke agent maintains its own state and reports back via message queues..." arch-guide.md 0.88
4 IMG-92 image null diagrams/message-flow.png 0.85
5 TXT-318 text "For high availability, deploy multiple orchestrator instances behind a load balancer..." deploy-guide.md 0.79

# Image metadata
table.images
id alt_text dimensions format
:IMG-89 "MAPLE hub-and-spoke architecture diagram" 1200x800 png
:IMG-92 "Agent message flow sequence diagram" 1400x600 png
```

---

## 3. Multi-Agent AI Systems

### Use Case: Agent State and Message Exchange

Agents need to share context, tasks, and results. ISON provides a clean protocol.

### Example: MAPLE Agent Communication

```
# Message from orchestrator to worker agent
object.message
id from to type timestamp
MSG-5001 :orchestrator :agent-research task 2025-01-20T10:15:00Z

# Task assignment
object.task
id type priority deadline
TASK-301 research high 2025-01-20T12:00:00Z

object.task_params
query max_sources include_academic
"Recent advances in mixture of experts models" 10 true

# Agent capabilities required
table.required_capabilities
capability min_level
web_search expert
paper_analysis intermediate
summarization expert

# Context from previous tasks
table.prior_context
task_id summary relevance
TASK-298 "User is researching efficient LLM architectures" high
TASK-299 "Previous query about sparse attention mechanisms" medium
```

---

### Example: Agent State Synchronization

```
# Agent registry and current states
table.agents
id name type status current_task last_heartbeat
:agent-001 orchestrator coordinator active null 2025-01-20T10:14:58Z
:agent-002 researcher worker active :TASK-301 2025-01-20T10:14:55Z
:agent-003 coder worker idle null 2025-01-20T10:14:50Z
:agent-004 reviewer worker active :TASK-299 2025-01-20T10:14:52Z

# Shared memory/blackboard
table.shared_memory
key value updated_by updated_at
user_goal "Build efficient RAG system" :agent-001 2025-01-20T09:00:00Z
tech_stack "Python, FAISS, Claude" :agent-003 2025-01-20T09:30:00Z
current_phase "research" :agent-001 2025-01-20T10:00:00Z
blockers "Need clarification on scale requirements" :agent-002 2025-01-20T10:10:00Z

# Message queue
table.pending_messages
id from to priority created
MSG-5002 :agent-002 :agent-001 high 2025-01-20T10:14:00Z
MSG-5003 :agent-004 :agent-003 medium 2025-01-20T10:12:00Z
```

---

## 4. Tool and Function Call Results

### Use Case: Structured Results from Tool Execution

When LLMs call tools, results should return in a token-efficient format.

### Example: Search Tool Results

```
# Tool call metadata
object.tool_call
id tool timestamp status
TC-8001 web_search 2025-01-20T10:20:00Z success

object.parameters
query max_results region
"ISON data format specification" 5 US

# Search results
table.results
rank title url snippet
1 "ISON: Interchange Simple Object Notation" github.com/ison-spec "A minimal, LLM-optimized data serialization format..."
2 "Comparing JSON, YAML, and ISON for AI" blog.example.com/formats "Token efficiency comparison shows ISON reduces..."
3 "ISON Parser Libraries" pypi.org/project/ison "Python reference implementation of the ISON v1.0 spec..."
4 "Building RAG with ISON" medium.com/@ai-arch "How ISON improves context window utilization..."
5 "ISON vs Protocol Buffers" dev.to/serialization "When to use text vs binary formats for AI..."
```

---

### Example: Database Query Tool

```
# Tool execution
object.tool_call
id tool timestamp status duration_ms
TC-8002 database_query 2025-01-20T10:22:00Z success 145

object.parameters
query database
"SELECT id, name, revenue FROM customers WHERE region = 'APAC' ORDER BY revenue DESC LIMIT 5" analytics_prod

# Query results
table.results
id name revenue
C-2001 "TechCorp Asia" 2450000.00
C-2015 "Pacific Industries" 1890000.00
C-2008 "Sunrise Ltd" 1245000.00
C-2042 "Eastern Partners" 980000.00
C-2019 "Harbor Group" 875000.00

# Query metadata
object.metadata
rows_returned total_matching execution_time_ms
5 23 145
```

---

### Example: Code Execution Tool

```
# Code execution result
object.tool_call
id tool timestamp status
TC-8003 code_interpreter 2025-01-20T10:25:00Z success

object.execution
language runtime duration_ms memory_mb
python 3.11 1250 128

# Output
object.output
stdout stderr return_value
"Processing complete.\nFound 42 anomalies.\n" "" 42

# Generated files
table.files
name path size_bytes type
anomalies.csv /output/anomalies.csv 15420 text/csv
chart.png /output/chart.png 48200 image/png
summary.json /output/summary.json 2840 application/json
```

---

### Example: API Integration Tool

```
# External API call result
object.tool_call
id tool timestamp status
TC-8004 http_request 2025-01-20T10:28:00Z success

object.request
method url
GET "https://api.weather.com/v1/current?city=Austin"

object.response
status_code content_type
200 application/json

# Parsed response data
object.data
city temperature_f humidity_pct conditions wind_mph
Austin 72 45 "Partly Cloudy" 8

# Rate limit info
object.rate_limit
remaining reset_at
95 2025-01-20T11:00:00Z
```

---

## 5. Database Query Outputs

### Use Case: Results from Relational, Vector, and Graph Databases

ISON handles all three paradigms—and hybrid queries that combine them.

### Example: Relational Query (PostgreSQL)

```
# Order details with joins
table.orders
order_id customer_name order_date total status items_count
5001 "Alice Johnson" 2025-01-15 234.50 shipped 3
5002 "Bob Smith" 2025-01-16 89.99 processing 1
5003 "Carol White" 2025-01-17 456.00 delivered 5
5004 "David Brown" 2025-01-18 123.45 pending 2
5005 "Eve Davis" 2025-01-19 678.90 shipped 4

# Aggregation results
object.summary
total_orders total_revenue avg_order_value orders_shipped
5 1582.84 316.57 2
```

---

### Example: Vector Search (Pinecone/FAISS)

```
# Semantic search results
object.query
vector_id namespace top_k
Q-VEC-001 products 10

table.matches
rank id score metadata.name metadata.category metadata.price
1 PROD-842 0.94 "Wireless Earbuds Pro" electronics 149.99
2 PROD-291 0.89 "Bluetooth Speaker" electronics 79.99
3 PROD-103 0.85 "USB-C Headphone Adapter" accessories 19.99
4 PROD-567 0.81 "Noise Canceling Headphones" electronics 299.99
5 PROD-234 0.78 "Portable Charger" accessories 49.99
```

---

### Example: Graph Query (Neo4j)

```
# Find shortest path between two people
object.query
type start_node end_node max_depth
shortest_path "Alice" "Frank" 5

# Path nodes
table.path_nodes
position id name type
1 :P001 Alice person
2 :P002 Bob person
3 :P005 Eve person
4 :P008 Frank person

# Path relationships
table.path_edges
from to relationship since
:P001 :P002 colleague 2020
:P002 :P005 friend 2018
:P005 :P008 sibling 1990

# Path metadata
object.path_info
length total_paths_found query_time_ms
3 2 45
```

---

### Example: Hybrid Query (RudraDB)

```
# Query: "Find similar products to user's purchase history, 
#         filter by in-stock, traverse to supplier info"

# Vector similarity matches
table.similar_products
rank product_id name similarity in_stock supplier
1 :PROD-842 "Ergonomic Keyboard" 0.94 true :SUP-10
2 :PROD-291 "Vertical Mouse" 0.91 true :SUP-10
3 :PROD-103 "Monitor Arm" 0.87 false :SUP-22
4 :PROD-567 "Standing Desk Mat" 0.82 true :SUP-15

# Supplier details (graph traversal)
table.suppliers
id name rating lead_time_days location
:SUP-10 "ErgoTech Inc" 4.8 3 "Austin, TX"
:SUP-15 "ComfortPlus" 4.5 5 "Seattle, WA"
:SUP-22 "DeskWorks" 4.2 7 "Portland, OR"

# User purchase history context
table.user_history
product_id name purchased_at
:PROD-100 "Laptop Stand" 2024-11-15
:PROD-205 "Wrist Rest" 2024-12-01
```

---

## 6. Knowledge Base Serialization

### Use Case: Ontologies, Taxonomies, and Domain Knowledge

Structured knowledge for LLM grounding and reasoning.

### Example: Product Taxonomy

```
# Category hierarchy
table.categories
id name parent level
CAT-1 Electronics null 0
CAT-2 Computers :CAT-1 1
CAT-3 Laptops :CAT-2 2
CAT-4 "Gaming Laptops" :CAT-3 3
CAT-5 "Business Laptops" :CAT-3 3
CAT-6 Desktops :CAT-2 2
CAT-7 Audio :CAT-1 1
CAT-8 Headphones :CAT-7 2
CAT-9 Speakers :CAT-7 2

# Category attributes
table.category_attributes
category_id attribute_name attribute_type required
:CAT-3 screen_size numeric true
:CAT-3 ram_gb numeric true
:CAT-3 storage_gb numeric true
:CAT-4 gpu_model text true
:CAT-4 refresh_rate numeric true
```

---

### Example: Medical Ontology

```
# Disease concepts
table.diseases
id name icd10_code category
DIS-001 "Type 2 Diabetes" E11 metabolic
DIS-002 Hypertension I10 cardiovascular
DIS-003 "Major Depression" F32 psychiatric

# Symptoms
table.symptoms
id name severity_levels
SYM-001 "Increased thirst" "mild,moderate,severe"
SYM-002 "Frequent urination" "mild,moderate,severe"
SYM-003 "Elevated blood pressure" "stage1,stage2,crisis"
SYM-004 "Persistent sadness" "mild,moderate,severe"

# Disease-symptom relationships
table.disease_symptoms
disease symptom frequency specificity
:DIS-001 :SYM-001 common high
:DIS-001 :SYM-002 common high
:DIS-002 :SYM-003 always high
:DIS-003 :SYM-004 always medium

# Contraindications
table.contraindications
drug_id disease_id severity reason
DRUG-101 :DIS-001 major "May cause hypoglycemia"
DRUG-205 :DIS-002 moderate "May elevate blood pressure"
```

---

### Example: Company Knowledge Base

```
# Organizational structure
table.departments
id name head budget_usd parent
DEPT-1 Engineering :EMP-001 5000000 null
DEPT-2 "AI Research" :EMP-010 2000000 :DEPT-1
DEPT-3 Platform :EMP-020 1500000 :DEPT-1
DEPT-4 Sales :EMP-030 3000000 null
DEPT-5 "Enterprise Sales" :EMP-031 2000000 :DEPT-4

# Key policies
table.policies
id title category effective_date
POL-001 "Remote Work Guidelines" HR 2024-01-01
POL-002 "Code Review Standards" Engineering 2024-03-15
POL-003 "Data Classification" Security 2024-02-01
POL-004 "Expense Approval Limits" Finance 2024-01-01

# Policy rules
table.policy_rules
policy_id rule_id condition action
:POL-004 R1 "amount < 100" "Self-approve"
:POL-004 R2 "amount >= 100 AND amount < 1000" "Manager approval"
:POL-004 R3 "amount >= 1000" "Director approval"
```

---

## 7. Agentic Workflows

### Use Case: Task Management, Execution Logs, and Decision Trees

Complex agent workflows need clear state representation.

### Example: Task Queue

```
# Pending tasks
table.task_queue
id type priority status assigned_to created deadline
TASK-101 research high in_progress :agent-002 2025-01-20T09:00:00Z 2025-01-20T12:00:00Z
TASK-102 code medium queued null 2025-01-20T09:15:00Z 2025-01-20T14:00:00Z
TASK-103 review high queued null 2025-01-20T09:30:00Z 2025-01-20T11:00:00Z
TASK-104 test low queued null 2025-01-20T09:45:00Z 2025-01-20T16:00:00Z

# Task dependencies
table.dependencies
task_id depends_on dependency_type
:TASK-102 :TASK-101 blocking
:TASK-103 :TASK-102 blocking
:TASK-104 :TASK-103 blocking

# Task parameters
table.task_params
task_id param_key param_value
:TASK-101 query "Best practices for ISON parser implementation"
:TASK-101 max_sources 5
:TASK-102 language python
:TASK-102 output_path src/parser.py
```

---

### Example: Execution Log

```
# Workflow execution trace
table.execution_log
seq timestamp agent action status duration_ms
1 2025-01-20T10:00:00Z :agent-001 "Received user request" success 5
2 2025-01-20T10:00:01Z :agent-001 "Parsed intent: build_parser" success 120
3 2025-01-20T10:00:02Z :agent-001 "Created task TASK-101" success 15
4 2025-01-20T10:00:03Z :agent-001 "Assigned to agent-002" success 8
5 2025-01-20T10:00:05Z :agent-002 "Started research" success 10
6 2025-01-20T10:01:00Z :agent-002 "Web search completed" success 55000
7 2025-01-20T10:01:05Z :agent-002 "Found 5 relevant sources" success 200
8 2025-01-20T10:02:00Z :agent-002 "Synthesizing findings" in_progress null

# Errors and retries
table.errors
seq agent error_type message retry_count resolved
6 :agent-002 timeout "Search API timeout" 1 true
```

---

### Example: Decision Tree Execution

```
# Decision tree definition
table.decision_nodes
id type condition true_branch false_branch action
N1 condition "user.tier == 'enterprise'" :N2 :N3 null
N2 condition "request.urgency == 'high'" :N4 :N5 null
N3 action null null null "Route to standard queue"
N4 action null null null "Assign senior agent immediately"
N5 action null null null "Assign within 1 hour"

# Current execution state
object.execution_state
current_node path_taken decision_made
:N4 "N1->N2->N4" "Assign senior agent immediately"

# Variables evaluated
table.evaluated_conditions
node condition value result
:N1 "user.tier == 'enterprise'" "user.tier = 'enterprise'" true
:N2 "request.urgency == 'high'" "request.urgency = 'high'" true
```

---

### Example: Plan and Execute Pattern

```
# Generated plan
object.plan
id goal created_by steps_count
PLAN-001 "Implement ISON parser in Rust" :agent-001 5

table.plan_steps
step_num description agent estimated_minutes dependencies status
1 "Research Rust parsing libraries" :agent-002 30 null completed
2 "Design module structure" :agent-003 20 1 completed
3 "Implement tokenizer" :agent-003 45 2 in_progress
4 "Implement type inference" :agent-003 30 3 pending
5 "Write unit tests" :agent-004 40 "3,4" pending

# Step outputs
table.step_outputs
step_num output_type content
1 recommendation "Use nom for parser combinators"
1 links "docs.rs/nom, github.com/nom-examples"
2 artifact "rust-parser-design.md"
```

---

## 8. Multimodal AI Systems

### Use Case: Vision, Audio, and Document Understanding Results

Structured outputs from multimodal models.

### Example: Object Detection Results

```
# Image metadata
object.image
id path dimensions format
IMG-001 uploads/street.jpg 1920x1080 jpeg

# Detected objects
table.detections
id label confidence bbox.x bbox.y bbox.w bbox.h
1 person 0.96 150 200 80 280
2 person 0.94 400 180 90 300
3 car 0.91 800 400 400 250
4 dog 0.87 200 450 100 80
5 "traffic light" 0.82 1200 50 40 120

# Scene classification
object.scene
primary_label confidence attributes
"urban street" 0.89 "daytime, sunny, crosswalk visible"
```

---

### Example: Video Understanding

```
# Video metadata
object.video
id path duration_sec fps resolution
VID-001 uploads/tutorial.mp4 324 30 1920x1080

# Scene segments
table.segments
id start end scene_type confidence
1 0.0 15.5 introduction 0.94
2 15.5 45.2 "code walkthrough" 0.91
3 45.2 120.8 demonstration 0.88
4 120.8 280.5 "detailed explanation" 0.90
5 280.5 324.0 conclusion 0.93

# Key moments
table.key_moments
timestamp type description
23.5 "code shown" "Function definition appears"
67.2 highlight "Important concept explained"
145.8 "error shown" "Common mistake demonstrated"
290.1 summary "Key takeaways listed"

# Transcript segments
table.transcript
segment_id start end speaker text
:1 0.0 15.5 host "Welcome to this tutorial on ISON parsing..."
:2 15.5 45.2 host "Let's look at the code structure..."
```

---

### Example: Document Understanding (OCR + Layout)

```
# Document metadata
object.document
id path pages format
DOC-001 uploads/invoice.pdf 1 pdf

# Extracted text blocks
table.text_blocks
id type content bbox.x bbox.y confidence
1 header "INVOICE" 50 30 0.99
2 field_label "Invoice Number:" 50 80 0.98
3 field_value "INV-2025-0042" 200 80 0.97
4 field_label "Date:" 400 80 0.98
5 field_value "January 20, 2025" 450 80 0.96
6 table_header "Description" 50 150 0.95
7 table_header "Quantity" 300 150 0.95
8 table_header "Price" 400 150 0.95
9 table_cell "Consulting Services" 50 180 0.94
10 table_cell "10" 300 180 0.97
11 table_cell "$1,500.00" 400 180 0.96

# Extracted structured data
object.invoice_data
invoice_number date vendor_name total_amount currency
"INV-2025-0042" 2025-01-20 "Acme Corp" 1500.00 USD

table.line_items
description quantity unit_price amount
"Consulting Services" 10 150.00 1500.00
```

---

### Example: Audio Transcription with Diarization

```
# Audio metadata
object.audio
id path duration_sec sample_rate channels
AUD-001 uploads/meeting.mp3 1845 44100 2

# Speaker identification
table.speakers
id label voice_characteristics
:SPK-1 "Speaker A" "male, deep voice"
:SPK-2 "Speaker B" "female, high pitch"
:SPK-3 "Speaker C" "male, accent detected"

# Transcription with timestamps
table.transcript
id start end speaker text confidence
1 0.0 5.2 :SPK-1 "Good morning everyone, let's begin." 0.95
2 5.5 12.8 :SPK-1 "Today we'll discuss the Q4 results." 0.93
3 13.2 18.5 :SPK-2 "Before that, can we review action items?" 0.91
4 19.0 35.2 :SPK-1 "Sure. John, you were handling the client outreach." 0.89
5 35.8 52.1 :SPK-3 "Yes, I've contacted 15 prospects so far..." 0.87

# Detected topics
table.topics
start end topic confidence
0.0 120.5 "Meeting opening and agenda" 0.88
120.5 680.2 "Q4 financial review" 0.92
680.2 1200.0 "Client outreach progress" 0.85
1200.0 1845.0 "Action items and next steps" 0.90
```

---

## Summary

These examples demonstrate ISON's versatility across the AI ecosystem:

| Use Case | Key ISON Benefits |
|----------|-------------------|
| **Prompt Engineering** | Pack more context in system prompts |
| **RAG Pipelines** | More retrieved chunks = better answers |
| **Multi-Agent Systems** | Clean protocol for agent communication |
| **Tool Results** | Structured outputs without JSON bloat |
| **Database Outputs** | Works for relational, vector, and graph |
| **Knowledge Bases** | Natural fit for ontologies and taxonomies |
| **Agentic Workflows** | Clear task queues, logs, and decision trees |
| **Multimodal AI** | Structured annotations for vision/audio/docs |

ISON becomes the common language between all these systems and LLMs—replacing JSON wherever token efficiency and LLM comprehension matter.
