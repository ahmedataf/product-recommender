from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional

from models import (
    RecommendationRequest,
    RecommendationResponse,
    Product,
)
from database import get_database
from recommendation_engine import get_recommendation_engine

app = FastAPI(
    title="Hisense Product Recommender API",
    description="AI-powered product search and recommendations for Hisense electronics",
    version="2.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def root():
    """Serve the main UI page."""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Hisense Product Recommender API", "docs": "/docs"}


@app.post("/api/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Get AI-powered product recommendations based on natural language query.

    Example queries:
    - "Best TV for gaming with 120Hz"
    - "Large fridge for family of 5"
    - "Washing machine for small family"
    - "Soundbar with Dolby Atmos"
    - "Projector for home cinema"
    """
    try:
        engine = get_recommendation_engine()
        return engine.get_recommendations(request.query)
    except Exception as e:
        import traceback
        print(f"Error in /api/recommend: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products", response_model=list[Product])
async def list_products(
    category: Optional[str] = None,
    brand: Optional[str] = None,
):
    """
    List all products with optional filtering.
    """
    db = get_database()
    brands = [brand] if brand else None
    return db.filter_products(
        category=category,
        brands=brands,
    )


@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """
    Get a single product by ID.
    """
    db = get_database()
    product = db.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/search")
async def search_products(q: str):
    """
    Search products by text query.
    """
    db = get_database()
    results = db.search_products(q)
    return {"query": q, "count": len(results), "products": results}


@app.get("/api/categories")
async def list_categories():
    """
    Get all available product categories.
    """
    db = get_database()
    categories = db.get_categories()
    return {
        "categories": [
            {
                "id": cat,
                "name": cat.replace("_", " ").title(),
                "count": len(db.get_products_by_category(cat))
            }
            for cat in categories
        ]
    }


@app.get("/api/brands")
async def list_brands(category: Optional[str] = None):
    """
    Get all available brands, optionally filtered by category.
    """
    db = get_database()
    return {"brands": db.get_brands(category)}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    db = get_database()
    products = db.get_all_products()
    categories = db.get_categories()
    return {
        "status": "healthy",
        "products_loaded": len(products),
        "categories": categories,
    }


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
