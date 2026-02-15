"""
ISONantic + Pydantic Composability Example

This example demonstrates using both libraries together:
- Pydantic for API layer (JSON request/response)
- ISONantic for LLM layer (token-efficient context)

Run with: python composed_app.py
Or with FastAPI: uvicorn composed_app:app --reload
"""

import sys
import os

# Add ison_format directory to path for isonantic import
# Goes up two levels: examples -> isonantic -> ison_format
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Optional
from datetime import datetime

# === Pydantic for API Layer ===
from pydantic import BaseModel, Field as PydanticField

class ProductSearchRequest(BaseModel):
    """API request - Pydantic for JSON"""
    query: str
    category: Optional[str] = None
    max_results: int = PydanticField(default=10, ge=1, le=50)
    user_id: Optional[int] = None

class ProductRecommendation(BaseModel):
    """API response item - Pydantic for JSON"""
    product_id: int
    name: str
    price: float
    reason: str
    confidence: float
    category: str

class SearchResponse(BaseModel):
    """API response - Pydantic for JSON"""
    query: str
    results: List[ProductRecommendation]
    processing_time_ms: int
    tokens_used: int
    tokens_saved: int  # vs JSON


# === ISONantic for LLM Layer ===
from isonantic import (
    TableModel, ObjectModel, ISONDocument,
    Field, Reference,
    parse_llm_output, prompt_for_model,
)

class Category(TableModel):
    """Product category"""
    __ison_block__ = "table.categories"
    id: int = Field(primary_key=True)
    name: str
    parent: Optional[Reference["Category"]] = None

class Product(TableModel):
    """Product in catalog"""
    __ison_block__ = "table.products"
    id: int = Field(primary_key=True)
    name: str
    price: float = Field(ge=0)
    category: Reference[Category]
    stock: int = Field(ge=0)

class UserPreference(TableModel):
    """User purchase history/preferences"""
    __ison_block__ = "table.user_prefs"
    user_id: int
    category: Reference[Category]
    purchase_count: int
    avg_price: float

class LLMRecommendation(TableModel):
    """LLM output format"""
    __ison_block__ = "table.recommendations"
    rank: int = Field(ge=1)
    product: Reference[Product]
    reason: str = Field(min_length=10)
    confidence: float = Field(ge=0, le=1)

class RAGContext(ISONDocument):
    """Context sent to LLM - token efficient!"""
    categories: List[Category]
    products: List[Product]
    user_prefs: List[UserPreference] = []
    
    class Config:
        block_order = ["categories", "products", "user_prefs"]


# === Mock Data ===
MOCK_CATEGORIES = [
    Category(id=1, name="Electronics", parent=None),
    Category(id=2, name="Laptops", parent=Reference(id="1")),
    Category(id=3, name="Accessories", parent=Reference(id="1")),
    Category(id=4, name="Home", parent=None),
]

MOCK_PRODUCTS = [
    Product(id=101, name="MacBook Pro 16", price=2499.99, category=Reference(id="2"), stock=50),
    Product(id=102, name="Dell XPS 15", price=1799.99, category=Reference(id="2"), stock=30),
    Product(id=103, name="USB-C Hub", price=49.99, category=Reference(id="3"), stock=200),
    Product(id=104, name="Wireless Mouse", price=29.99, category=Reference(id="3"), stock=500),
    Product(id=105, name="Smart Speaker", price=99.99, category=Reference(id="4"), stock=100),
]

MOCK_USER_PREFS = {
    1: [
        UserPreference(user_id=1, category=Reference(id="2"), purchase_count=3, avg_price=2000),
        UserPreference(user_id=1, category=Reference(id="3"), purchase_count=5, avg_price=40),
    ],
    2: [
        UserPreference(user_id=2, category=Reference(id="4"), purchase_count=2, avg_price=150),
    ],
}


# === Comparison: JSON vs ISON Context Size ===
def compare_token_usage():
    """Show token savings of ISON vs JSON"""
    import json
    
    # Build context
    context = RAGContext(
        categories=MOCK_CATEGORIES,
        products=MOCK_PRODUCTS,
        user_prefs=MOCK_USER_PREFS.get(1, [])
    )
    
    # ISON format
    ison_context = context.to_ison()
    
    # JSON format (what Pydantic would produce)
    json_context = json.dumps(context.dict(), indent=2)
    
    # Rough token estimation (1 token ≈ 4 chars)
    ison_tokens = len(ison_context) // 4
    json_tokens = len(json_context) // 4
    savings = (json_tokens - ison_tokens) / json_tokens * 100
    
    print("=" * 60)
    print("TOKEN COMPARISON: ISON vs JSON")
    print("=" * 60)
    print(f"\nISON Context ({ison_tokens} tokens):")
    print("-" * 40)
    print(ison_context)
    print(f"\nJSON Context ({json_tokens} tokens):")
    print("-" * 40)
    print(json_context[:500] + "..." if len(json_context) > 500 else json_context)
    print(f"\n{'=' * 60}")
    print(f"ISON: ~{ison_tokens} tokens")
    print(f"JSON: ~{json_tokens} tokens")
    print(f"SAVINGS: {savings:.1f}%")
    print("=" * 60)
    
    return ison_tokens, json_tokens


# === Simulated LLM Call ===
def mock_llm_call(context_ison: str, query: str) -> str:
    """
    Simulate LLM response.
    In production, this would call OpenAI/Anthropic/etc.
    """
    # LLM would return ISON-formatted recommendations
    return """
Based on your query and preferences, here are my recommendations:

table.recommendations
rank product reason confidence
1 :101 "Perfect for professional work with excellent performance" 0.95
2 :102 "Great alternative with similar specs at lower price" 0.85
3 :103 "Essential accessory for laptop connectivity" 0.75

These products match your interest in high-quality electronics.
"""


# === Main Workflow ===
def process_search(request: ProductSearchRequest) -> SearchResponse:
    """
    Complete workflow:
    1. Pydantic validates API request
    2. ISONantic builds token-efficient LLM context
    3. ISONantic parses LLM output
    4. Pydantic formats API response
    """
    import time
    start = time.time()
    
    # 1. Build ISONantic context (token-efficient)
    user_prefs = MOCK_USER_PREFS.get(request.user_id, [])
    
    # Filter products by category if specified (include child categories)
    products = MOCK_PRODUCTS
    if request.category:
        # Find matching categories and their children
        cat_ids = set()
        for c in MOCK_CATEGORIES:
            if request.category.lower() in c.name.lower():
                cat_ids.add(c.id)
        # Add children (categories with parent in cat_ids)
        for c in MOCK_CATEGORIES:
            if c.parent and c.parent.id in [str(cid) for cid in cat_ids]:
                cat_ids.add(c.id)
        products = [p for p in products if int(p.category.id) in cat_ids]
    
    context = RAGContext(
        categories=MOCK_CATEGORIES,
        products=products,
        user_prefs=user_prefs
    )
    
    # 2. Convert to ISON for LLM
    context_ison = context.to_ison()
    
    # Calculate token savings
    import json
    json_size = len(json.dumps(context.dict()))
    ison_size = len(context_ison)
    tokens_used = ison_size // 4
    tokens_saved = (json_size - ison_size) // 4
    
    # 3. Build prompt with ISON format instructions
    prompt = f"""
User query: {request.query}

Context (product catalog and user preferences):
{context_ison}

{prompt_for_model(LLMRecommendation)}

Provide up to {request.max_results} recommendations.
"""
    
    # 4. Call LLM (mocked)
    llm_response = mock_llm_call(context_ison, request.query)
    
    # 5. Parse LLM output with ISONantic (validated!)
    recommendations = parse_llm_output(llm_response, LLMRecommendation)
    
    # 6. Convert to Pydantic response format
    results = []
    # Build lookup tables for manual resolution
    products_by_id = {str(p.id): p for p in context.products}
    categories_by_id = {str(c.id): c for c in context.categories}

    for rec in recommendations[:request.max_results]:
        # Manually resolve references (product ID from LLM output)
        product_id = rec.product.id
        product = products_by_id.get(product_id)
        if not product:
            continue

        category = categories_by_id.get(product.category.id)
        category_name = category.name if category else "Unknown"

        results.append(ProductRecommendation(
            product_id=product.id,
            name=product.name,
            price=product.price,
            reason=rec.reason,
            confidence=rec.confidence,
            category=category_name
        ))
    
    elapsed = int((time.time() - start) * 1000)
    
    # 7. Return Pydantic response
    return SearchResponse(
        query=request.query,
        results=results,
        processing_time_ms=elapsed,
        tokens_used=tokens_used,
        tokens_saved=tokens_saved
    )


# === FastAPI App (optional) ===
try:
    from fastapi import FastAPI
    
    app = FastAPI(
        title="ISONantic + Pydantic Demo",
        description="Demonstrating composability of both libraries"
    )
    
    @app.post("/search", response_model=SearchResponse)
    async def search_products(request: ProductSearchRequest):
        """
        Search products with LLM-powered recommendations.
        
        - **Pydantic** handles API request/response validation
        - **ISONantic** handles token-efficient LLM context
        """
        return process_search(request)
    
    @app.get("/schema/api")
    async def get_api_schema():
        """Get Pydantic JSON Schema for API"""
        return {
            "request": ProductSearchRequest.model_json_schema(),
            "response": SearchResponse.model_json_schema()
        }
    
    @app.get("/schema/llm")
    async def get_llm_schema():
        """Get ISONantic schemas for LLM layer"""
        return {
            "context": RAGContext.model_json_schema(),
            "output": LLMRecommendation.model_json_schema(),
            "prompt_format": prompt_for_model(LLMRecommendation)
        }

except ImportError:
    app = None
    print("FastAPI not installed. Running standalone demo.")


# === Standalone Demo ===
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ISONantic + Pydantic Composability Demo")
    print("=" * 60)
    
    # Show token savings
    ison_tokens, json_tokens = compare_token_usage()
    
    # Demo search workflow
    print("\n" + "=" * 60)
    print("SEARCH WORKFLOW DEMO")
    print("=" * 60)
    
    # Create request (Pydantic)
    request = ProductSearchRequest(
        query="I need a powerful laptop for software development",
        category="Electronics",
        max_results=3,
        user_id=1
    )
    
    print(f"\nAPI Request (Pydantic):")
    print(request.model_dump_json(indent=2))
    
    # Process (ISONantic internally)
    response = process_search(request)
    
    print(f"\nAPI Response (Pydantic):")
    print(response.model_dump_json(indent=2))
    
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"[OK] Pydantic: Validated API request/response")
    print(f"[OK] ISONantic: Token-efficient LLM context")
    print(f"[OK] ISONantic: Validated LLM output parsing")
    print(f"[OK] Tokens used: {response.tokens_used}")
    print(f"[OK] Tokens saved vs JSON: {response.tokens_saved} ({response.tokens_saved/(response.tokens_used+response.tokens_saved)*100:.1f}%)")
    print(f"[OK] Processing time: {response.processing_time_ms}ms")
