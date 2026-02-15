# Using ISON with OpenAI API and LLM Boundaries

## The Critical Distinction: Protocol vs Content

---

## The Answer: Yes, But Not How You Might Think

### OpenAI API Structure

```python
# OpenAI API call
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "What's the weather?"
        }
    ]
)
```

**The API protocol itself is JSON.** You can't change that—OpenAI expects JSON requests.

---

## Where ISON Goes: Inside the Content

### Traditional Approach (JSON in Content)

```python
# Build context as JSON
context = {
    "user": {"name": "Alice", "tier": "premium"},
    "products": [
        {"id": 1, "name": "Widget", "price": 29.99},
        {"id": 2, "name": "Gadget", "price": 49.99}
    ]
}

# Send to OpenAI
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": "You are a shopping assistant."
        },
        {
            "role": "user",
            "content": f"Context: {json.dumps(context, indent=2)}\n\nRecommend products."
        }
    ]
)
```

**Problem:** The JSON context inside `content` consumes tokens inefficiently.

---

## ISON Approach (ISON in Content)

```python
import ison_parser

# Build context as Python objects
context = {
    "user": {"name": "Alice", "tier": "premium"},
    "products": [
        {"id": 1, "name": "Widget", "price": 29.99},
        {"id": 2, "name": "Gadget", "price": 49.99}
    ]
}

# Convert to ISON
ison_context = ison_parser.dumps(ison_parser.from_dict(context))

# Send to OpenAI (API still uses JSON protocol)
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": "You are a shopping assistant."
        },
        {
            "role": "user",
            "content": f"Context:\n{ison_context}\n\nRecommend products."
        }
    ]
)
```

**Key insight:** The OpenAI API call is still JSON, but the *text content* inside messages is ISON.

---

## Visual Breakdown

```
┌─────────────────────────────────────────┐
│      OpenAI API Request (JSON)          │
│                                         │
│  {                                      │
│    "model": "gpt-4",                    │
│    "messages": [                        │
│      {                                  │
│        "role": "user",                  │
│        "content": "                     │  ← This is where ISON goes
│          table.products                 │     (as text)
│          id name price                  │
│          1 Widget 29.99                 │
│          2 Gadget 49.99                 │
│        "                                │
│      }                                  │
│    ]                                    │
│  }                                      │
└─────────────────────────────────────────┘
```

---

## Token Counting Example

### JSON in Content

```python
context = json.dumps({
    "products": [
        {"id": 1, "name": "Widget", "price": 29.99},
        {"id": 2, "name": "Gadget", "price": 49.99},
        {"id": 3, "name": "Gizmo", "price": 19.99}
    ]
}, indent=2)

content = f"Context: {context}\n\nRecommend products."

# Estimate: ~150 tokens
```

### ISON in Content

```python
ison_context = """table.products
id name price
1 Widget 29.99
2 Gadget 49.99
3 Gizmo 19.99"""

content = f"Context:\n{ison_context}\n\nRecommend products."

# Estimate: ~95 tokens
# Savings: 37%
```

---

## Complete Working Example

```python
import openai
import ison_parser

def recommend_products(user_data, products, query):
    """
    Call OpenAI with ISON-formatted context
    """
    
    # 1. Build context as Python objects
    context = {
        "user": user_data,
        "products": products
    }
    
    # 2. Convert to ISON
    ison_doc = ison_parser.from_dict(context)
    ison_text = ison_parser.dumps(ison_doc)
    
    # 3. Call OpenAI API (protocol is JSON, content is ISON)
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are a shopping assistant. Context is in ISON format."
            },
            {
                "role": "user",
                "content": f"""Context:
{ison_text}

User Query: {query}

Provide recommendations based on the context."""
            }
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content


# Usage
user = {"name": "Alice", "tier": "premium", "budget": 100}
products = [
    {"id": 1, "name": "Widget", "price": 29.99, "category": "electronics"},
    {"id": 2, "name": "Gadget", "price": 49.99, "category": "electronics"},
    {"id": 3, "name": "Gizmo", "price": 19.99, "category": "accessories"}
]

result = recommend_products(user, products, "What should I buy?")
print(result)
```

---

## Does the LLM Understand ISON?

**Yes, natively.** You don't need to tell it "this is ISON format" (though you can). The LLM sees:

```
table.products
id name price
1 Widget 29.99
2 Gadget 49.99
```

And immediately understands it's tabular data—it's trained on millions of similar patterns (CSV, TSV, Markdown tables).

---

## Comparison: What Goes Where

| Layer | Format | Example |
|-------|--------|---------|
| **HTTP Request** | JSON | `POST /v1/chat/completions` |
| **Request Body** | JSON | `{"model": "gpt-4", "messages": [...]}` |
| **Message Structure** | JSON | `{"role": "user", "content": "..."}` |
| **Message Content** | **ISON** | `table.products\nid name price\n...` |
| **HTTP Response** | JSON | `{"choices": [...]}` |
| **Response Content** | Text | LLM's answer (natural language) |

---

## Other LLM APIs

This applies to all LLM APIs:

### Anthropic Claude

```python
import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": f"Context:\n{ison_context}\n\nAnswer: {query}"
        }
    ]
)
```

### Google Gemini

```python
import google.generativeai as genai

model = genai.GenerativeModel('gemini-pro')
response = model.generate_content(f"Context:\n{ison_context}\n\n{query}")
```

### Local Models (Ollama, llama.cpp)

```python
import requests

response = requests.post('http://localhost:11434/api/generate', json={
    "model": "llama2",
    "prompt": f"Context:\n{ison_context}\n\n{query}"
})
```

**All of these APIs use JSON for protocol, but ISON goes in the text content.**

---

## When NOT to Use ISON in API Content

### 1. Simple Text Queries

```python
# Don't convert this to ISON
query = "What is the capital of France?"

# Just send directly
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": query}]
)
```

### 2. Already Short Context

If your context is 3 items, the overhead isn't worth it:

```python
# Not worth converting
context = {"user": "Alice", "age": 30, "city": "NYC"}

# Just use JSON or plain text
content = f"User: Alice, Age: 30, City: NYC\n\nQuery: ..."
```

### 3. Unstructured Content

```python
# This isn't tabular/structured
long_article = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit...
[2000 words of prose]
"""

# Don't convert to ISON, send as-is
```

---

## The Decision Matrix

| Context Type | Size | Use ISON? | Why |
|--------------|------|-----------|-----|
| Tabular data | 10+ rows | ✅ Yes | 30-70% token savings |
| Multiple tables | Any | ✅ Yes | Clear structure + savings |
| Structured objects | 5+ fields | ✅ Yes | Flat representation |
| Simple text | Any | ❌ No | No structure to optimize |
| 1-3 objects | Small | ❌ No | Overhead not worth it |
| Prose/documents | Any | ❌ No | Not structured data |

---

## Real-World Token Savings

### Scenario: Product Recommendation API

**Setup:** 20 products, 5 fields each

**JSON in content:**
```python
products_json = json.dumps([
    {"id": 1, "name": "Widget", "price": 29.99, "stock": 15, "rating": 4.5},
    {"id": 2, "name": "Gadget", "price": 49.99, "stock": 8, "rating": 4.7},
    # ... 18 more
])

# Token count: ~800 tokens
```

**ISON in content:**
```python
products_ison = """table.products
id name price stock rating
1 Widget 29.99 15 4.5
2 Gadget 49.99 8 4.7
... (18 more rows)
"""

# Token count: ~520 tokens
# Savings: 280 tokens (35%)
```

**Monthly savings (1000 API calls/day):**
- 30,000 calls × 280 tokens saved = 8.4M tokens/month
- At $0.003/1K tokens: **$25.20/month saved**

---

## Updated Architecture Diagram

```
Your Application
      │
      ├─ Build Python objects (dict/list)
      │
      ├─ Convert to ISON text
      │     ↓
      │  ison_text = ison_parser.dumps(data)
      │
      ├─ Construct API request (JSON protocol)
      │     ↓
      │  {
      │    "model": "gpt-4",
      │    "messages": [
      │      {"role": "user", "content": ison_text}  ← ISON as text
      │    ]
      │  }
      │
      └─ Send to OpenAI API
            ↓
         HTTP POST (JSON)
            ↓
         OpenAI processes
            ↓
         Response (JSON protocol)
            ↓
         Extract text answer
```

---

## Best Practice Template

```python
def call_llm_with_context(user_query: str, context_data: dict) -> str:
    """
    Standard pattern for calling LLM with ISON context
    
    Args:
        user_query: The user's question
        context_data: Structured data to include as context
        
    Returns:
        LLM's response text
    """
    import openai
    import ison_parser
    
    # Convert context to ISON
    ison_context = ison_parser.dumps(
        ison_parser.from_dict(context_data)
    )
    
    # Call OpenAI (JSON protocol, ISON content)
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": f"""Context:
{ison_context}

Question: {user_query}

Provide a detailed answer using the context."""
            }
        ]
    )
    
    return response.choices[0].message.content
```

---

## Complete Example: RAG Application

```python
import openai
import ison_parser
from typing import List, Dict

class RAGSystem:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    def query(self, question: str, retrieved_docs: List[Dict]) -> str:
        """
        Answer question using retrieved documents
        
        Args:
            question: User's question
            retrieved_docs: List of documents from vector search
            
        Returns:
            LLM's answer
        """
        # Convert retrieved docs to ISON
        context_data = {"retrieved_documents": retrieved_docs}
        ison_context = ison_parser.dumps(
            ison_parser.from_dict(context_data)
        )
        
        # Call LLM with ISON context
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Answer questions using the provided context."
                },
                {
                    "role": "user",
                    "content": f"""Context:
{ison_context}

Question: {question}

Please provide a detailed answer based on the context."""
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content


# Usage example
rag = RAGSystem(api_key="your-api-key")

# Simulated vector search results
docs = [
    {
        "id": "doc_42",
        "content": "ISON is a token-efficient data format...",
        "score": 0.94,
        "source": "ison-docs.md"
    },
    {
        "id": "doc_17",
        "content": "JSON uses more tokens due to repeated keys...",
        "score": 0.89,
        "source": "format-comparison.md"
    }
]

answer = rag.query("What is ISON?", docs)
print(answer)
```

---

## Advanced: Streaming Responses

When using streaming, ISON still goes in the initial context:

```python
def stream_with_ison_context(query: str, context_data: dict):
    """
    Stream LLM responses with ISON context
    """
    import openai
    import ison_parser
    
    # Convert to ISON
    ison_context = ison_parser.dumps(
        ison_parser.from_dict(context_data)
    )
    
    # Stream responses
    stream = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{ison_context}\n\n{query}"
            }
        ],
        stream=True  # Enable streaming
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="")
```

---

## Error Handling

```python
def safe_llm_call(query: str, context_data: dict) -> dict:
    """
    Call LLM with proper error handling
    """
    try:
        # Convert to ISON
        ison_context = ison_parser.dumps(
            ison_parser.from_dict(context_data)
        )
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": f"Context:\n{ison_context}\n\n{query}"
                }
            ]
        )
        
        return {
            "success": True,
            "answer": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens
        }
        
    except openai.APIError as e:
        return {
            "success": False,
            "error": f"API error: {str(e)}"
        }
    except ison_parser.ISONError as e:
        return {
            "success": False,
            "error": f"ISON conversion error: {str(e)}"
        }
```

---

## Monitoring and Metrics

Track token savings over time:

```python
class ISONMetrics:
    def __init__(self):
        self.total_json_tokens = 0
        self.total_ison_tokens = 0
    
    def log_conversion(self, json_size: int, ison_size: int):
        """Track token savings"""
        self.total_json_tokens += json_size
        self.total_ison_tokens += ison_size
    
    def get_savings(self) -> dict:
        """Calculate overall savings"""
        saved = self.total_json_tokens - self.total_ison_tokens
        percent = (saved / self.total_json_tokens) * 100
        
        return {
            "tokens_saved": saved,
            "percent_saved": percent,
            "json_tokens": self.total_json_tokens,
            "ison_tokens": self.total_ison_tokens
        }

# Usage
metrics = ISONMetrics()

# Track each conversion
json_size = len(tiktoken_encode(json_str))
ison_size = len(tiktoken_encode(ison_str))
metrics.log_conversion(json_size, ison_size)

# Get stats
print(metrics.get_savings())
```

---

## Bottom Line

| Question | Answer |
|----------|--------|
| **Should I use ISON with OpenAI API?** | Yes, in message content |
| **Does the API protocol change?** | No, still JSON |
| **Where does ISON go?** | Inside the `content` field as text |
| **Does GPT understand ISON?** | Yes, zero-shot |
| **Will it save tokens?** | Yes, 30-50% for structured data |
| **Is it worth the conversion?** | Yes, if context > 10 items |

---

## Summary

### ✅ Do This

- **Use JSON** for the API protocol (you have no choice)
- **Use ISON** inside message content for structured data
- **Convert at the boundary** right before the API call
- **Track savings** to measure impact

### ❌ Don't Do This

- **Don't try to change** the API protocol itself
- **Don't convert** simple text or prose
- **Don't use ISON** for tiny datasets (< 5 items)
- **Don't forget** the LLM understands ISON natively

### 💡 Key Insight

> The API speaks JSON.  
> The message content can be ISON.  
> This is where the token savings happen.

---

**TL;DR:** Use ISON **inside** the API's message content, not as the API protocol itself. The API speaks JSON; the message content can be ISON for 30-70% token savings on structured data.

---

*ISON: Efficient interchange at the LLM boundary.*
