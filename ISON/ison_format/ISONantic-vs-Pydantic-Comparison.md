# ISONantic vs Pydantic: Real-World Usage Comparison

## When to Use Each

| Scenario | Pydantic | ISONantic | Winner |
|----------|----------|-----------|--------|
| REST API request/response | ✅ Best | ⚠️ Possible | Pydantic |
| LLM context window data | ⚠️ Token-heavy | ✅ 30-60% smaller | ISONantic |
| Database → LLM pipelines | ⚠️ Manual refs | ✅ Native refs | ISONantic |
| Graph/relational data | ⚠️ Manual FKs | ✅ First-class refs | ISONantic |
| FastAPI integration | ✅ Native | ⚠️ Manual | Pydantic |
| Multi-agent systems | ⚠️ Verbose | ✅ Compact | ISONantic |
| RAG pipelines | ⚠️ Token cost | ✅ Efficient | ISONantic |
| Config files | ✅ JSON/YAML | ✅ ISON | Tie |
| Browser/frontend | ✅ JSON native | ⚠️ Parse needed | Pydantic |

---

## Advantage 1: Token Efficiency (ISONantic)

### The Problem
LLM context windows are expensive. Every token counts.

### JSON/Pydantic Approach
```python
from pydantic import BaseModel
from typing import List

class OrderItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float

class Order(BaseModel):
    order_id: int
    customer_id: int
    customer_name: str
    items: List[OrderItem]

# Serialized JSON (~450 tokens for 3 orders)
{
    "orders": [
        {
            "order_id": 1001,
            "customer_id": 101,
            "customer_name": "John Smith",
            "items": [
                {"product_id": 1, "product_name": "Laptop", "quantity": 1, "unit_price": 999.99},
                {"product_id": 2, "product_name": "Mouse", "quantity": 2, "unit_price": 29.99}
            ]
        },
        {
            "order_id": 1002,
            "customer_id": 102,
            "customer_name": "Jane Doe",
            "items": [
                {"product_id": 3, "product_name": "Keyboard", "quantity": 1, "unit_price": 79.99}
            ]
        }
    ]
}
```

### ISON/ISONantic Approach
```python
from isonantic import TableModel, ISONDocument, Field, Reference

class Customer(TableModel):
    __ison_block__ = "table.customers"
    id: int = Field(primary_key=True)
    name: str

class Product(TableModel):
    __ison_block__ = "table.products"
    id: int = Field(primary_key=True)
    name: str
    price: float

class OrderItem(TableModel):
    __ison_block__ = "table.order_items"
    order: Reference["Order"]
    product: Reference[Product]
    quantity: int

class Order(TableModel):
    __ison_block__ = "table.orders"
    id: int = Field(primary_key=True)
    customer: Reference[Customer]

# Serialized ISON (~180 tokens - 60% smaller!)
"""
table.customers
id name
101 "John Smith"
102 "Jane Doe"

table.products
id name price
1 Laptop 999.99
2 Mouse 29.99
3 Keyboard 79.99

table.orders
id customer
1001 :101
1002 :102

table.order_items
order product quantity
:1001 :1 1
:1001 :2 2
:1002 :3 1
"""
```

### Token Comparison

| Format | Tokens | Cost (GPT-4) | Context Used |
|--------|--------|--------------|--------------|
| JSON | ~450 | $0.0135 | 0.35% of 128K |
| ISON | ~180 | $0.0054 | 0.14% of 128K |
| **Savings** | **60%** | **$0.0081** | **0.21%** |

At scale (1M requests/month): **$8,100 saved**

---

## Advantage 2: First-Class References (ISONantic)

### The Problem
Relational/graph data requires foreign key handling.

### Pydantic: Manual Foreign Keys
```python
from pydantic import BaseModel
from typing import Optional

class Team(BaseModel):
    id: int
    name: str
    manager_id: Optional[int] = None  # FK to User - no type safety!

class User(BaseModel):
    id: int
    name: str
    team_id: int  # FK to Team - just an int, could be anything
    manager_id: Optional[int] = None  # FK to User

# Usage: Manual resolution required
users = [User(**u) for u in data["users"]]
teams = {t.id: Team(**t) for t in data["teams"]}

# Get user's team - manual lookup
user = users[0]
team = teams.get(user.team_id)  # No type hints, could be None

# Validation? None. user.team_id = 99999 is valid
```

### ISONantic: Typed References
```python
from isonantic import TableModel, ISONDocument, Field, Reference
from typing import Optional, List

class Team(TableModel):
    __ison_block__ = "table.teams"
    id: int = Field(primary_key=True)
    name: str
    manager: Optional[Reference["User"]] = None  # Typed!

class User(TableModel):
    __ison_block__ = "table.users"
    id: int = Field(primary_key=True)
    name: str
    team: Reference[Team]  # Typed reference to Team
    manager: Optional[Reference["User"]] = None  # Self-reference

class OrgDocument(ISONDocument):
    teams: List[Team]
    users: List[User]

# Parse with automatic reference validation
doc = OrgDocument.parse(ison_data)
# ValidationError if any reference is invalid!

# Usage: Type-safe resolution
user = doc.users[0]
team = user.team.resolve(doc)  # Returns Team, not Optional[Team]
print(team.name)  # IDE knows this is a Team!

# Manager chain
if user.manager:
    mgr = user.manager.resolve(doc)  # Returns User
    mgr_team = mgr.team.resolve(doc)  # Returns Team
```

### Reference Validation Comparison

| Feature | Pydantic | ISONantic |
|---------|----------|-----------|
| Type-safe references | ❌ | ✅ `Reference[Team]` |
| Automatic validation | ❌ | ✅ On parse |
| IDE autocomplete on resolve | ❌ | ✅ |
| Invalid ref detection | ❌ Manual | ✅ Automatic |
| Self-references | ⚠️ Tricky | ✅ Native |
| Circular references | ⚠️ Complex | ✅ Supported |

---

## Advantage 3: Multi-Block Documents (ISONantic)

### The Problem
Related data often comes in multiple tables/collections.

### Pydantic: Nested or Separate
```python
# Option 1: Deeply nested (verbose, repetitive)
class FullOrder(BaseModel):
    order_id: int
    customer: Customer  # Embedded, duplicated if same customer
    items: List[OrderItemWithProduct]  # Each has full product

# Option 2: Separate models (no unified parsing)
orders = [Order(**o) for o in data["orders"]]
customers = [Customer(**c) for c in data["customers"]]
products = [Product(**p) for p in data["products"]]
# Manual assembly required
```

### ISONantic: Unified Document
```python
class ECommerceDocument(ISONDocument):
    """Complete e-commerce data in one schema"""
    customers: List[Customer]
    products: List[Product]
    categories: List[Category]
    orders: List[Order]
    order_items: List[OrderItem]
    
    class Config:
        block_order = ["categories", "customers", "products", "orders", "order_items"]
        validate_refs = True  # Validate all references across blocks

# Single parse, all validated
doc = ECommerceDocument.parse(ison_data)

# Cross-block queries are natural
def get_order_details(doc: ECommerceDocument, order_id: int):
    order = next(o for o in doc.orders if o.id == order_id)
    customer = order.customer.resolve(doc)
    items = [
        {
            "product": item.product.resolve(doc).name,
            "quantity": item.quantity,
            "price": item.product.resolve(doc).price
        }
        for item in doc.order_items
        if item.order.id == str(order_id)
    ]
    return {"customer": customer.name, "items": items}
```

---

## Advantage 4: LLM Output Parsing (ISONantic)

### The Problem
LLMs generate structured data with formatting inconsistencies.

### Pydantic: Manual Extraction
```python
import json
import re
from pydantic import BaseModel, ValidationError

class Recommendation(BaseModel):
    rank: int
    product_id: int
    reason: str
    confidence: float

def parse_llm_recommendations(response: str) -> list[Recommendation]:
    # Step 1: Extract JSON from response
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if not json_match:
        # Try to find raw JSON
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
    
    if not json_match:
        raise ValueError("No JSON found in response")
    
    # Step 2: Parse JSON
    try:
        data = json.loads(json_match.group(1) if '```' in response else json_match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    # Step 3: Validate with Pydantic
    results = []
    errors = []
    for i, item in enumerate(data):
        try:
            results.append(Recommendation(**item))
        except ValidationError as e:
            errors.append(f"Item {i}: {e}")
    
    if errors:
        raise ValueError(f"Validation errors: {errors}")
    
    return results
```

### ISONantic: Built-in LLM Parsing
```python
from isonantic import TableModel, Field, Reference, parse_llm_output, LLMParseError

class Recommendation(TableModel):
    __ison_block__ = "table.recommendations"
    rank: int = Field(ge=1)
    product: Reference["Product"]
    reason: str
    confidence: float = Field(ge=0, le=1)

# One line - handles extraction, parsing, validation
try:
    recommendations = parse_llm_output(
        llm_response,
        Recommendation,
        auto_fix=True  # Fix common LLM mistakes
    )
except LLMParseError as e:
    print(f"Error: {e}")
    print(f"Suggestion: {e.suggestion}")
    # Retry prompt available
```

### LLM Prompt Generation
```python
from isonantic import prompt_for_model

# Generate format instructions for LLM
prompt = prompt_for_model(Recommendation)
print(prompt)
# Output format (ISON):
# table.recommendations
# rank product reason confidence
# <int >=1> <ref:products> <str> <float 0-1>
```

---

## Advantage 5: Database Alignment (ISONantic)

### SQL Query Results
```python
# Pydantic: Convert rows to nested objects
rows = cursor.fetchall()
# Manual: Group by order, nest items, resolve FKs

# ISONantic: Direct table mapping
class QueryResult(ISONDocument):
    orders: List[Order]
    customers: List[Customer]
    
# SQL result → ISON → Validated models
doc = QueryResult.parse(sql_to_ison(rows))
```

### Graph Database (Neo4j)
```python
# Pydantic: Flatten graph to JSON
# Loses relationship semantics

# ISONantic: References ARE relationships
class Person(TableModel):
    __ison_block__ = "table.persons"
    id: str = Field(primary_key=True)
    name: str
    knows: List[Reference["Person"]]  # Graph edge!
    works_at: Reference["Company"]

# Neo4j → ISON preserves graph structure
"""
table.persons
id name knows works_at
alice Alice [:bob,:charlie] :acme
bob Bob [:alice] :globex

table.companies
id name
acme "Acme Corp"
globex "Globex Inc"
"""
```

---

## Composability: Using Both Together

### Scenario: FastAPI with LLM Backend

```python
from fastapi import FastAPI
from pydantic import BaseModel
from isonantic import TableModel, ISONDocument, parse_llm_output, Reference
from typing import List

app = FastAPI()

# === Pydantic for API layer ===
class RecommendationRequest(BaseModel):
    """API request model (Pydantic for JSON API)"""
    user_id: int
    category: str
    limit: int = 5

class RecommendationResponse(BaseModel):
    """API response model (Pydantic for JSON API)"""
    product_id: int
    product_name: str
    reason: str
    confidence: float

# === ISONantic for LLM layer ===
class Product(TableModel):
    __ison_block__ = "table.products"
    id: int = Field(primary_key=True)
    name: str
    category: str
    price: float

class LLMRecommendation(TableModel):
    __ison_block__ = "table.recommendations"
    rank: int
    product: Reference[Product]
    reason: str
    confidence: float

class RAGContext(ISONDocument):
    """Efficient context for LLM"""
    products: List[Product]
    user_history: List["PurchaseHistory"]

# === Compose them ===
@app.post("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(request: RecommendationRequest):
    # 1. Build ISON context (token-efficient)
    products = get_products_by_category(request.category)
    history = get_user_history(request.user_id)
    
    context = RAGContext(products=products, user_history=history)
    context_ison = context.to_ison()  # 60% fewer tokens!
    
    # 2. Call LLM with ISON context
    llm_response = await call_llm(
        f"Given this context:\n{context_ison}\n\n"
        f"Recommend {request.limit} products for user."
    )
    
    # 3. Parse LLM output with ISONantic
    recommendations = parse_llm_output(llm_response, LLMRecommendation)
    
    # 4. Convert to Pydantic for API response
    return [
        RecommendationResponse(
            product_id=rec.product.resolve(context).id,
            product_name=rec.product.resolve(context).name,
            reason=rec.reason,
            confidence=rec.confidence
        )
        for rec in recommendations[:request.limit]
    ]
```

### Architecture Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI                               │
│  ┌─────────────────┐              ┌─────────────────┐       │
│  │    Pydantic     │              │    Pydantic     │       │
│  │  Request Model  │              │  Response Model │       │
│  └────────┬────────┘              └────────▲────────┘       │
│           │                                │                 │
│           ▼                                │                 │
│  ┌─────────────────────────────────────────┴───────────┐    │
│  │                  Business Logic                      │    │
│  └─────────────────────────┬───────────────────────────┘    │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM Layer                               │
│  ┌─────────────────┐              ┌─────────────────┐       │
│  │   ISONantic     │              │   ISONantic     │       │
│  │  RAG Context    │─────────────▶│  Output Parser  │       │
│  │  (60% smaller)  │     LLM      │  (validated)    │       │
│  └─────────────────┘              └─────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Decision Matrix

### Use Pydantic When:
- ✅ Building REST APIs (FastAPI, Django)
- ✅ Frontend/browser JSON consumption
- ✅ Standard JSON ecosystem tools needed
- ✅ Team already knows Pydantic
- ✅ No LLM/token concerns

### Use ISONantic When:
- ✅ LLM context window is a concern
- ✅ Working with relational/graph data
- ✅ Database → LLM pipelines
- ✅ Multi-agent systems (compact messages)
- ✅ RAG with structured retrieval
- ✅ Need reference validation
- ✅ Token costs matter at scale

### Use Both When:
- ✅ FastAPI frontend + LLM backend
- ✅ JSON API with ISON internal processing
- ✅ Gradual migration to token efficiency
- ✅ Different teams (API team vs ML team)

---

## Summary

| Dimension | Pydantic | ISONantic |
|-----------|----------|-----------|
| **Ecosystem** | Massive | Growing |
| **JSON interop** | Native | Via conversion |
| **Token efficiency** | ❌ Verbose | ✅ 30-60% smaller |
| **References** | ❌ Manual FKs | ✅ First-class |
| **LLM parsing** | ❌ DIY | ✅ Built-in |
| **Schema export** | ✅ JSON Schema | ✅ JSON Schema + ISON |
| **FastAPI** | ✅ Native | ⚠️ Manual integration |
| **Learning curve** | Low (familiar) | Low (similar API) |

**Bottom line**: 
- **Pydantic** = JSON APIs, web services, general Python
- **ISONantic** = LLM workflows, databases, token-sensitive applications
- **Both together** = Full-stack AI applications
