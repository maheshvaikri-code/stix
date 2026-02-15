# ISONantic Use Cases

## Real-World Applications for Token-Efficient LLM Workflows

---

## Overview

ISONantic shines in scenarios where:
- **Token efficiency matters** (LLM context windows, API costs)
- **Data is relational** (foreign keys, references between entities)
- **Structure is tabular** (database outputs, spreadsheets, logs)
- **LLM output needs validation** (structured generation)

---

## 1. RAG Pipelines

### Problem
Retrieved documents consume context window. JSON metadata is verbose.

### Solution
Compact document representation with deduplicated references.

```python
from isonantic import TableModel, ISONDocument, Field, Reference

class Document(TableModel):
    __ison_block__ = "table.documents"
    id: str = Field(primary_key=True)
    title: str
    source: str

class Chunk(TableModel):
    __ison_block__ = "table.chunks"
    id: str = Field(primary_key=True)
    doc: Reference[Document]
    content: str
    score: float = Field(ge=0, le=1)

class RAGContext(ISONDocument):
    documents: List[Document]
    chunks: List[Chunk]
```

### ISON Output
```
table.documents
id title source
D1 "Q3 Report" finance
D2 "Product Roadmap" planning

table.chunks
id doc content score
C1 :D1 "Revenue grew 15%..." 0.94
C2 :D1 "Margins improved..." 0.87
C3 :D2 "Q1 features include..." 0.82
```

### Impact
| Format | Tokens | Savings |
|--------|--------|---------|
| JSON | ~800 | - |
| ISON | ~320 | **60%** |

---

## 2. Multi-Agent Systems

### Problem
Agent messages are token-heavy. No built-in reference validation.

### Solution
Compact messaging with typed references between agents, tasks, and artifacts.

```python
class Agent(TableModel):
    __ison_block__ = "table.agents"
    id: str = Field(primary_key=True)
    role: str

class Task(TableModel):
    __ison_block__ = "table.tasks"
    id: str = Field(primary_key=True)
    assigned_to: Reference[Agent]
    status: str = Field(choices=["pending", "done"])

class Message(TableModel):
    __ison_block__ = "table.messages"
    from_agent: Reference[Agent]
    to_agent: Reference[Agent]
    content: str
```

### ISON Output
```
table.agents
id role
planner Planner
coder Coder
reviewer Reviewer

table.tasks
id assigned_to status
T1 :coder pending
T2 :reviewer pending

table.messages
from_agent to_agent content
:planner :coder "Implement the login API"
:coder :reviewer "Ready for review"
```

---

## 3. Text-to-SQL Agents

### Problem
Database schemas consume context. Query results are verbose in JSON.

### Solution
Natural table format for schemas and results.

```python
class SchemaColumn(TableModel):
    __ison_block__ = "table.schema"
    table_name: str
    column: str
    type: str
    is_pk: bool
    fk: Optional[str] = None
```

### Schema Context
```
table.schema
table_name column type is_pk fk
customers id int true null
customers name varchar false null
orders id int true null
orders customer_id int false customers.id
orders total decimal false null
```

### Query Result
```
table.result
customer_name order_count total_spent
"John Smith" 5 1250.00
"Jane Doe" 3 890.50
```

---

## 4. LLM Structured Output

### Problem
Parsing LLM output is error-prone. No validation.

### Solution
Built-in prompt generation and validated parsing.

```python
from isonantic import prompt_for_model, parse_llm_output

class Entity(TableModel):
    __ison_block__ = "table.entities"
    text: str
    type: str = Field(choices=["person", "org", "location"])
    confidence: float = Field(ge=0, le=1)

# Generate format instructions
prompt = prompt_for_model(Entity)
# "Output format (ISON):
#  table.entities
#  text type confidence
#  <str> <person/org/location> <float 0-1>"

# Parse with validation
entities = parse_llm_output(llm_response, Entity)
```

### LLM Output
```
table.entities
text type confidence
"Apple Inc." org 0.98
"Tim Cook" person 0.95
"Cupertino" location 0.90
```

---

## 5. Database-to-LLM Pipelines

### Problem
ORM to JSON loses FK relationships. Nested JSON is verbose.

### Solution
Direct table export with typed references.

```python
class Customer(TableModel):
    __ison_block__ = "table.customers"
    id: int = Field(primary_key=True)
    name: str

class Order(TableModel):
    __ison_block__ = "table.orders"
    id: int = Field(primary_key=True)
    customer: Reference[Customer]
    total: float
```

### ISON Export
```
table.customers
id name
1 "Acme Corp"
2 "TechStart"

table.orders
id customer total
101 :1 5000.00
102 :1 3500.00
103 :2 1200.00
```

---

## 6. Knowledge Graphs

### Problem
Graph data flattened to JSON loses edge semantics.

### Solution
References naturally represent graph edges.

```python
class Person(TableModel):
    __ison_block__ = "table.persons"
    id: str = Field(primary_key=True)
    name: str

class Knows(TableModel):
    __ison_block__ = "table.knows"
    person1: Reference[Person]
    person2: Reference[Person]
    since: str

class WorksAt(TableModel):
    __ison_block__ = "table.works_at"
    person: Reference[Person]
    company: Reference["Company"]
    role: str
```

### Graph in ISON
```
table.persons
id name
alice "Alice Chen"
bob "Bob Smith"

table.companies
id name
acme "Acme Corp"

table.knows
person1 person2 since
:alice :bob 2020

table.works_at
person company role
:alice :acme CEO
:bob :acme CTO
```

---

## 7. E-Commerce Recommendations

### Problem
Product catalogs + user history = large context.

### Solution
Compact catalog with behavior references.

```python
class Product(TableModel):
    __ison_block__ = "table.products"
    id: int = Field(primary_key=True)
    name: str
    price: float

class UserAction(TableModel):
    __ison_block__ = "table.actions"
    product: Reference[Product]
    action: str = Field(choices=["view", "cart", "buy"])
    count: int

class Recommendation(TableModel):
    __ison_block__ = "table.recs"
    product: Reference[Product]
    reason: str
    score: float
```

### Context
```
table.products
id name price
1 "MacBook Pro" 2499
2 "USB-C Hub" 49
3 "Monitor" 599

table.actions
product action count
:1 view 5
:2 buy 1

table.recs
product reason score
:3 "Complements MacBook" 0.92
:2 "Frequently bought together" 0.85
```

---

## 8. Document Extraction

### Problem
Extracted fields need structure and validation.

### Solution
Hierarchical sections with field references.

```python
class Section(TableModel):
    __ison_block__ = "table.sections"
    id: str = Field(primary_key=True)
    parent: Optional[Reference["Section"]] = None
    title: str

class Field(TableModel):
    __ison_block__ = "table.fields"
    section: Reference[Section]
    name: str
    value: str
    confidence: float
```

### Contract Extraction
```
table.sections
id parent title
S1 null "Parties"
S2 null "Terms"
S3 :S2 "Payment"

table.fields
section name value confidence
:S1 party_a "Acme Inc" 0.98
:S1 party_b "TechCorp" 0.97
:S3 amount "$50,000" 0.95
:S3 due_date "2024-03-01" 0.90
```

---

## 9. Log Analysis

### Problem
Raw logs consume tokens. No structure for analysis.

### Solution
Structured logs with service references.

```python
class Service(TableModel):
    __ison_block__ = "table.services"
    id: str = Field(primary_key=True)
    name: str

class Log(TableModel):
    __ison_block__ = "table.logs"
    time: str
    service: Reference[Service]
    level: str = Field(choices=["INFO", "WARN", "ERROR"])
    message: str

class Metric(TableModel):
    __ison_block__ = "table.metrics"
    service: Reference[Service]
    name: str
    value: float
```

### Incident Context
```
table.services
id name
api "API Gateway"
db "Database"

table.logs
time service level message
10:15:32 :api ERROR "Connection timeout"
10:15:33 :db WARN "Pool exhausted"

table.metrics
service name value
:api error_rate 15.5
:db connections 95
```

---

## 10. Healthcare Records

### Problem
Medical data is sensitive and structured. Context efficiency critical.

### Solution
Patient-centric references with validation.

```python
class Patient(TableModel):
    __ison_block__ = "table.patients"
    id: str = Field(primary_key=True)
    age: int
    sex: str = Field(choices=["M", "F"])

class Diagnosis(TableModel):
    __ison_block__ = "table.diagnoses"
    patient: Reference[Patient]
    code: str
    status: str = Field(choices=["active", "resolved"])

class Medication(TableModel):
    __ison_block__ = "table.medications"
    patient: Reference[Patient]
    drug: str
    dosage: str
```

### Clinical Context
```
table.patients
id age sex
P1 65 M

table.diagnoses
patient code status
:P1 I10 active
:P1 E11 active

table.medications
patient drug dosage
:P1 Lisinopril 10mg
:P1 Metformin 500mg
```

---

## 11. Financial Portfolios

### Problem
Portfolio data is naturally tabular. JSON adds overhead.

### Solution
Holdings with security references and computed fields.

```python
class Security(TableModel):
    __ison_block__ = "table.securities"
    symbol: str = Field(primary_key=True)
    name: str
    sector: str

class Holding(TableModel):
    __ison_block__ = "table.holdings"
    security: Reference[Security]
    shares: int
    cost: float
    price: float
    
    @computed
    def value(self) -> float:
        return self.shares * self.price
    
    @computed
    def gain(self) -> float:
        return (self.price - self.cost) * self.shares
```

### Portfolio
```
table.securities
symbol name sector
AAPL "Apple" Tech
MSFT "Microsoft" Tech

table.holdings
security shares cost price
:AAPL 100 150.00 185.00
:MSFT 50 280.00 410.00
```

---

## 12. Fine-Tuning Data

### Problem
JSONL is verbose for training data.

### Solution
ISONL for compact streaming format.

```python
class Example(TableModel):
    __ison_block__ = "table.examples"
    instruction: str
    input: str
    output: str

class Preference(TableModel):
    __ison_block__ = "table.prefs"
    prompt: str
    chosen: str
    rejected: str
    score: float
```

### ISONL (one block per line)
```
table.ex|instruction input output|"Summarize" "Long text..." "Summary"
table.ex|instruction input output|"Translate" "Hello" "Hola"
```

---

## Summary: When to Use ISONantic

| Use Case | Token Savings | Primary Benefit |
|----------|---------------|-----------------|
| RAG Pipelines | 50-70% | Document deduplication |
| Multi-Agent | 60-75% | Compact messaging |
| Text-to-SQL | 50-70% | Natural table format |
| Structured Output | - | Validated parsing |
| Database-to-LLM | 50-70% | Reference integrity |
| Knowledge Graphs | 40-60% | Edge representation |
| E-Commerce | 55-65% | Catalog efficiency |
| Document Extraction | 50-60% | Hierarchical structure |
| Log Analysis | 40-50% | Service references |
| Healthcare | 50-65% | Patient-centric refs |
| Financial | 45-55% | Portfolio structure |
| Fine-Tuning | 30-40% | ISONL streaming |

---

## Getting Started

```python
pip install isonantic

from isonantic import TableModel, Field, parse_ison

class User(TableModel):
    __ison_block__ = "table.users"
    id: int = Field(primary_key=True)
    name: str

users = parse_ison("""
table.users
id name
1 Alice
2 Bob
""", User)

print(users[0].name)  # Alice
```

---

*For complete documentation, see [ISONantic Specification](./ISONantic-Specification.md)*
