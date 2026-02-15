# ISONantic Specification

## A Pydantic-like Data Validation Library for ISON

**Version:** 1.0.0  
**Status:** Draft  
**Author:** Mahesh Vaikri  
**Date:** January 2025

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Design Goals](#2-design-goals)
3. [Core Concepts](#3-core-concepts)
4. [Model Definition](#4-model-definition)
5. [Field Types](#5-field-types)
6. [References](#6-references)
7. [Validation](#7-validation)
8. [Parsing](#8-parsing)
9. [Serialization](#9-serialization)
10. [Document Schema](#10-document-schema)
11. [Advanced Features](#11-advanced-features)
12. [LLM Integration](#12-llm-integration)
13. [API Reference](#13-api-reference)
14. [Examples](#14-examples)
15. [Comparison with Pydantic](#15-comparison-with-pydantic)

---

## 1. Introduction

### 1.1 What is ISONantic?

ISONantic is a data validation and serialization library for ISON (Interchange Simple Object Notation), inspired by Pydantic's approach to JSON. It provides:

- **Type-safe models** for ISON blocks
- **Automatic validation** during parsing
- **Reference resolution** across blocks
- **Schema generation** for documentation
- **LLM output parsing** with error recovery

### 1.2 Why ISONantic?

While the base ISON parser handles syntax, ISONantic adds:

| Feature | Base Parser | ISONantic |
|---------|-------------|-----------|
| Type inference | ✅ | ✅ |
| Schema validation | ❌ | ✅ |
| Reference validation | ❌ | ✅ |
| Reference resolution | ❌ | ✅ |
| Custom validators | ❌ | ✅ |
| Computed fields | ❌ | ✅ |
| Python type hints | ❌ | ✅ |
| IDE autocompletion | ❌ | ✅ |
| Error messages | Basic | Detailed |

### 1.3 Installation

```bash
pip install isonantic
```

### 1.4 Quick Example

```python
from isonantic import TableModel, Field, Reference

class Team(TableModel):
    __ison_block__ = "table.teams"
    
    id: int = Field(primary_key=True)
    name: str

class User(TableModel):
    __ison_block__ = "table.users"
    
    id: int = Field(primary_key=True)
    name: str
    email: str = Field(pattern=r"^[\w.-]+@[\w.-]+\.\w+$")
    team: Reference[Team]

# Parse and validate
from isonantic import parse_ison

ison_data = """
table.teams
id name
10 "AI Research"

table.users
id name email team
101 Mahesh mahesh@example.com :10
"""

users = parse_ison(ison_data, User)
for user in users:
    print(f"{user.name} is on team {user.team.resolve().name}")
```

---

## 2. Design Goals

### 2.1 Primary Goals

1. **Pydantic-familiar API**: Developers who know Pydantic should feel at home
2. **Reference-first**: Native support for ISON's `:ID` references
3. **Validation at parse time**: Catch errors early with clear messages
4. **Type safety**: Full Python type hint support
5. **LLM-friendly**: Easy parsing of LLM-generated ISON

### 2.2 Non-Goals

1. **Replacing Pydantic**: ISONantic is for ISON, Pydantic is for JSON
2. **General serialization**: Focus is ISON, not arbitrary formats
3. **ORM functionality**: Not a database abstraction layer

---

## 3. Core Concepts

### 3.1 Models

Models define the structure of ISON blocks:

```python
from isonantic import TableModel, ObjectModel

class Product(TableModel):
    """A product in the catalog"""
    __ison_block__ = "table.products"
    
    id: int
    name: str
    price: float

class Config(ObjectModel):
    """Application configuration"""
    __ison_block__ = "object.config"
    
    timeout: int
    debug: bool
```

### 3.2 Model Types

| Type | ISON Block | Rows | Use Case |
|------|------------|------|----------|
| `TableModel` | `table.*` | Multiple | Lists, collections |
| `ObjectModel` | `object.*` | Single | Config, metadata |
| `MetaModel` | `meta.*` | Single | Schema, version info |

### 3.3 Fields

Fields define column types and constraints:

```python
from isonantic import Field

class User(TableModel):
    id: int = Field(primary_key=True)
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w.-]+@[\w.-]+\.\w+$")
    age: int = Field(ge=0, le=150)
    score: float = Field(default=0.0)
```

### 3.4 References

References link records across blocks:

```python
from isonantic import Reference

class Order(TableModel):
    id: int
    customer: Reference[Customer]  # Links to Customer model
    items: list[Reference[Product]]  # Multiple references
```

### 3.5 Documents

Documents combine multiple models:

```python
from isonantic import ISONDocument

class ECommerceDoc(ISONDocument):
    customers: list[Customer]
    products: list[Product]
    orders: list[Order]
```

---

## 4. Model Definition

### 4.1 Basic Model

```python
from isonantic import TableModel

class User(TableModel):
    __ison_block__ = "table.users"  # Required: maps to ISON block
    
    id: int
    name: str
    active: bool = True  # Default value
```

### 4.2 Model Configuration

```python
class User(TableModel):
    __ison_block__ = "table.users"
    
    class Config:
        # Validation options
        strict: bool = False  # Allow type coercion
        extra: str = "forbid"  # "allow", "ignore", "forbid"
        
        # Serialization options
        ison_align: bool = True  # Align columns in output
```

### 4.3 Inheritance

```python
class BaseEntity(TableModel):
    id: int = Field(primary_key=True)
    created_at: str
    updated_at: str

class User(BaseEntity):
    __ison_block__ = "table.users"
    
    name: str
    email: str
```

---

## 5. Field Types

### 5.1 Basic Types

| Python Type | ISON Type | Example |
|-------------|-----------|---------|
| `int` | integer | `42` |
| `float` | float | `3.14` |
| `str` | string | `Alice`, `"New York"` |
| `bool` | boolean | `true`, `false` |
| `None` | null | `null` |

### 5.2 Field Constraints

```python
from isonantic import Field

class Product(TableModel):
    # Numeric constraints
    price: float = Field(ge=0)  # >= 0
    quantity: int = Field(gt=0, le=1000)  # > 0 and <= 1000
    
    # String constraints
    sku: str = Field(min_length=3, max_length=20)
    name: str = Field(pattern=r"^[A-Z].*")  # Must start with uppercase
    
    # Enum/choices
    status: str = Field(choices=["active", "inactive", "discontinued"])
    
    # Primary key
    id: int = Field(primary_key=True)
    
    # Unique constraint
    email: str = Field(unique=True)
    
    # Nullable
    description: str = Field(default=None, nullable=True)
```

### 5.3 Optional Fields

```python
from typing import Optional

class User(TableModel):
    id: int
    name: str
    nickname: Optional[str] = None  # Can be null
    bio: str = ""  # Empty string default
```

### 5.4 Nested Fields (Dot-Paths)

```python
from isonantic import Nested

class Address(ISONModel):
    street: str
    city: str
    state: str
    zip: str = None

class Customer(TableModel):
    __ison_block__ = "table.customers"
    
    id: int
    name: str
    address: Nested[Address]  # Maps to address.street, address.city, etc.
```

Parses ISON:
```
table.customers
id name address.street address.city address.state address.zip
1 "John Smith" "123 Main St" Dallas TX 75001
```

---

## 6. References

### 6.1 Basic References

```python
from isonantic import Reference

class Team(TableModel):
    __ison_block__ = "table.teams"
    id: int = Field(primary_key=True)
    name: str

class User(TableModel):
    __ison_block__ = "table.users"
    id: int
    name: str
    team: Reference[Team]  # ← Reference to Team
```

ISON:
```
table.teams
id name
10 "AI Research"

table.users
id name team
101 Mahesh :10
```

### 6.2 Reference Resolution

```python
from isonantic import ISONDocument

doc = ISONDocument.parse(ison_data)

# Get user and resolve team
user = doc.users[0]
team = user.team.resolve(doc)
print(team.name)  # "AI Research"
```

### 6.3 Self-References

```python
class Category(TableModel):
    __ison_block__ = "table.categories"
    
    id: int = Field(primary_key=True)
    name: str
    parent: Optional[Reference["Category"]] = None  # Self-reference
```

### 6.4 Reference Validation

```python
from isonantic import ValidationError

try:
    doc = ISONDocument.parse(ison_data)
except ValidationError as e:
    # Reference :999 not found errors
    print(e.errors())
```

---

## 7. Validation

### 7.1 Automatic Validation

Validation happens during parsing:

```python
from isonantic import parse_ison, ValidationError

ison_data = """
table.users
id name email age
1 Alice invalid-email 25
2 Bob bob@test.com -5
"""

try:
    users = parse_ison(ison_data, User)
except ValidationError as e:
    print(e.errors())
    # [
    #   {"loc": ("users", 0, "email"), "msg": "Invalid email format"},
    #   {"loc": ("users", 1, "age"), "msg": "Value must be >= 0"}
    # ]
```

### 7.2 Field Validators

```python
from isonantic import validator

class User(TableModel):
    id: int
    name: str
    email: str
    
    @validator("email")
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Must contain @")
        return v.lower()  # Transform value
```

### 7.3 Root Validators

```python
from isonantic import root_validator

class DateRange(TableModel):
    start_date: str
    end_date: str
    
    @root_validator
    def validate_dates(cls, values):
        start = values.get("start_date")
        end = values.get("end_date")
        if start and end and start > end:
            raise ValueError("start_date must be before end_date")
        return values
```

### 7.4 Computed Fields

```python
from isonantic import computed

class OrderSummary(TableModel):
    order_id: int
    subtotal: float
    tax_rate: float
    
    @computed
    def tax(self) -> float:
        return round(self.subtotal * self.tax_rate, 2)
    
    @computed
    def total(self) -> float:
        return round(self.subtotal + self.tax, 2)
```

---

## 8. Parsing

### 8.1 Parse Single Model

```python
from isonantic import parse_ison

ison_data = """
table.users
id name email
1 Alice alice@test.com
2 Bob bob@test.com
"""

users = parse_ison(ison_data, User)
# Returns: list[User]
```

### 8.2 Parse Document

```python
from isonantic import ISONDocument

class MyDocument(ISONDocument):
    users: list[User]
    teams: list[Team]
    orders: list[Order]

doc = MyDocument.parse(ison_data)
print(doc.users)
print(doc.teams)
```

### 8.3 Safe Parsing

```python
from isonantic import parse_ison_safe

result = parse_ison_safe(ison_data, User)

if result.success:
    users = result.data
else:
    print(f"Errors: {result.errors}")
    print(f"Partial data: {result.partial_data}")  # Valid rows only
```

---

## 9. Serialization

### 9.1 Model to ISON

```python
# Multiple models (table)
users = [user1, user2, user3]
print(User.to_ison_table(users))
# table.users
# id name email team
# 1 Alice alice@test.com :10
# 2 Bob bob@test.com :10
```

### 9.2 Document to ISON

```python
doc = MyDocument(
    users=[user1, user2],
    teams=[team1],
    orders=[order1, order2]
)

print(doc.to_ison())
```

### 9.3 To Dict/JSON

```python
# Model to dict
user_dict = user.dict()

# Model to JSON
user_json = user.json(indent=2)

# Document to dict
doc_dict = doc.dict()

# Document to JSON
doc_json = doc.json(indent=2)
```

---

## 10. Document Schema

### 10.1 Define Document Schema

```python
from isonantic import ISONDocument
from typing import List

class ECommerceSchema(ISONDocument):
    """E-commerce data schema"""
    
    # Required blocks
    customers: List[Customer]
    products: List[Product]
    
    # Optional blocks
    orders: List[Order] = []
    
    class Config:
        # Block parsing order (for reference resolution)
        block_order = ["customers", "products", "orders"]
```

### 10.2 Schema Validation

```python
# Validate entire document
doc = ECommerceSchema.parse(ison_data)

# All references validated
# All types validated
# All constraints validated
```

### 10.3 JSON Schema Export (OpenAPI Compatible)

ISONantic generates standard JSON Schema for API documentation and OpenAPI integration:

```python
# Model JSON Schema
schema = User.model_json_schema()
print(schema)
# {
#     "$schema": "https://json-schema.org/draft/2020-12/schema",
#     "title": "User",
#     "type": "object",
#     "properties": {
#         "id": {"type": "integer"},
#         "name": {"type": "string", "minLength": 1, "maxLength": 100},
#         "email": {"type": "string", "pattern": "..."},
#         "team": {"type": "string", "x-ison-ref": "Team"}
#     },
#     "required": ["id", "name", "email", "team"]
# }

# As JSON string
schema_json = User.model_json_schema_json(indent=2)

# Pydantic v1 compatible aliases
schema = User.schema()  # Same as model_json_schema()
schema_json = User.schema_json()  # Same as model_json_schema_json()
```

#### Document JSON Schema

```python
from isonantic import document_json_schema, openapi_schema

# Full document schema with $defs for each model
schema = ECommerceSchema.model_json_schema()

# OpenAPI components/schemas format
components = openapi_schema(ECommerceSchema)
# Returns: {"schemas": {"Customer": {...}, "Product": {...}, ...}}
```

### 10.4 ISON Schema Export

```python
from isonantic import generate_schema

# Generate ISON-native schema
ison_schema = generate_schema(User)
```

---

## 11. LLM Integration

### 11.1 Structured Output Prompting

```python
from isonantic import prompt_for_model

prompt = prompt_for_model(ProductRecommendation)
print(prompt)
# Output format (ISON):
# table.recommendations
# rank product reason confidence
# <int> <ref:products> <str> <float 0-1>
```

### 11.2 Parse LLM Response

```python
from isonantic import parse_llm_output, LLMParseError

try:
    recommendations = parse_llm_output(
        llm_response,
        ProductRecommendation,
        strict=False,  # Be lenient with LLM formatting
        auto_fix=True,  # Attempt to fix common LLM mistakes
    )
except LLMParseError as e:
    print(f"Could not parse LLM output: {e}")
    print(f"Suggested fix: {e.suggestion}")
```

---

## 12. API Reference

### 12.1 Core Classes

```python
# Base model classes
class ISONModel: ...
class TableModel(ISONModel): ...
class ObjectModel(ISONModel): ...
class MetaModel(ISONModel): ...

# Document class
class ISONDocument: ...

# Field definition
class Field: ...

# Reference types
class Reference[T]: ...
class LazyReference[T]: ...

# Nested field
class Nested[T]: ...
```

### 12.2 Parsing Functions

```python
def parse_ison(data: str, model: Type[T], ...) -> List[T]: ...
def parse_ison_safe(data: str, model: Type[T], ...) -> ParseResult[T]: ...
def parse_llm_output(response: str, model: Type[T], ...) -> List[T]: ...
```

### 12.3 Validation

```python
# Decorators
def validator(field: str, *, pre: bool = False, post: bool = False): ...
def root_validator(*, pre: bool = False): ...
def computed(func): ...

# Exceptions
class ValidationError(Exception): ...
class ReferenceError(Exception): ...
class LLMParseError(Exception): ...
```

### 12.4 Field Parameters

```python
Field(
    # Identity
    primary_key: bool = False,
    unique: bool = False,
    alias: str = None,
    
    # Type constraints
    nullable: bool = False,
    default: Any = ...,
    default_factory: Callable = None,
    
    # Numeric constraints
    gt: float = None,  # Greater than
    ge: float = None,  # Greater or equal
    lt: float = None,  # Less than
    le: float = None,  # Less or equal
    
    # String constraints
    min_length: int = None,
    max_length: int = None,
    pattern: str = None,  # Regex pattern
    
    # Enum constraint
    choices: List[Any] = None,
    
    # Documentation
    title: str = None,
    description: str = None,
)
```

---

## 13. Comparison with Pydantic

### Feature Comparison

| Feature | Pydantic | ISONantic |
|---------|----------|-----------|
| **Target Format** | JSON | ISON |
| **Type Validation** | ✅ | ✅ |
| **Nested Objects** | Via nesting | Via dot-paths |
| **References** | ❌ | ✅ First-class |
| **Reference Validation** | ❌ | ✅ |
| **Reference Resolution** | ❌ | ✅ |
| **Table Awareness** | ❌ | ✅ |
| **Multi-Block Docs** | ❌ | ✅ |
| **JSON Schema Export** | ✅ | ✅ |
| **ISON Schema Export** | ❌ | ✅ |
| **OpenAPI Compatible** | ✅ | ✅ |
| **LLM Output Parsing** | Manual | Built-in |
| **Computed Fields** | ✅ | ✅ |
| **Validators** | ✅ | ✅ |

### Syntax Comparison

**Pydantic (JSON):**
```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str
    team_id: int  # Manual foreign key
```

**ISONantic (ISON):**
```python
from isonantic import TableModel, Field, Reference

class User(TableModel):
    __ison_block__ = "table.users"
    id: int
    name: str
    team: Reference[Team]  # Typed reference!
```

---

## 14. Best Practices

### 1. Always Define Primary Keys
```python
class User(TableModel):
    id: int = Field(primary_key=True)  # ← Required for references
```

### 2. Use Type Hints
```python
# Good
team: Reference[Team]

# Avoid
team: Reference  # Missing type parameter
```

### 3. Handle LLM Output Gracefully
```python
result = parse_ison_safe(response, Model)
if not result.success:
    # Retry with better prompt
    pass
```

### 4. Document Your Models
```python
class User(TableModel):
    """User account in the system"""
    __ison_block__ = "table.users"
    
    id: int = Field(description="Unique user identifier")
    email: str = Field(description="User's email address")
```

---

*End of ISONantic Specification*
