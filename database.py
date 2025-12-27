import json
import re
from pathlib import Path
from typing import Optional
from models import Product, ProductCategory


def detect_category(product_name: str, specs: dict) -> ProductCategory:
    """Detect product category from name and specs."""
    name_lower = product_name.lower()
    specs_str = json.dumps(specs).lower()

    # Projector detection (check BEFORE TV since laser TVs are projectors)
    if any(kw in name_lower for kw in ["projector", "laser cinema"]):
        return ProductCategory.PROJECTOR
    if "projection_size" in specs or "throw_distance" in specs or "throw_ratio" in specs_str:
        return ProductCategory.PROJECTOR

    # Dishwasher detection (check early)
    if "dishwasher" in name_lower:
        return ProductCategory.DISHWASHER

    # TV detection
    if any(kw in name_lower for kw in ["tv", "uled", "qled", "miniled", "mini-led", "uhd"]):
        return ProductCategory.TV
    if "display_sizes" in specs or "resolution" in specs_str and "4k" in specs_str:
        return ProductCategory.TV

    # Refrigerator detection
    if any(kw in name_lower for kw in ["refrigerator", "fridge", "freezer"]):
        return ProductCategory.REFRIGERATOR
    if "refrigerator" in specs_str or "freezer" in specs_str:
        return ProductCategory.REFRIGERATOR

    # Washing machine detection
    if any(kw in name_lower for kw in ["washing machine", "washer", "front load", "top load"]):
        if "dryer" in name_lower and "combo" in name_lower:
            return ProductCategory.WASHING_MACHINE  # Combo units
        return ProductCategory.WASHING_MACHINE

    # Dryer detection
    if "dryer" in name_lower and "washer" not in name_lower:
        return ProductCategory.DRYER

    # AC detection
    if any(kw in name_lower for kw in ["ac", "air conditioner", "inverter", "split", "wall mounted"]):
        return ProductCategory.AC
    if "tonnage" in specs_str or "btu" in specs_str or "cooling" in specs_str:
        return ProductCategory.AC

    # Soundbar detection
    if any(kw in name_lower for kw in ["soundbar", "sound bar", "speaker"]):
        return ProductCategory.SOUNDBAR
    if "channels" in specs or "subwoofer" in specs_str:
        return ProductCategory.SOUNDBAR

    # Dishwasher detection
    if "dishwasher" in name_lower:
        return ProductCategory.DISHWASHER

    # Default fallback - try to detect from specs
    if "display" in specs_str or "screen" in specs_str:
        return ProductCategory.TV

    return ProductCategory.TV  # Default


def extract_sizes(specs: dict, product_name: str) -> list[str]:
    """Extract available sizes from specs or product name."""
    sizes = []

    # Check common size fields
    for key in ["display_sizes", "available_sizes", "screen_sizes", "sizes"]:
        if key in specs and isinstance(specs[key], list):
            sizes.extend(specs[key])

    # Extract capacity info
    capacity_match = re.search(r'(\d+)\s*L', product_name, re.IGNORECASE)
    if capacity_match:
        sizes.append(f"{capacity_match.group(1)}L")

    capacity_match = re.search(r'(\d+)\s*kg', product_name, re.IGNORECASE)
    if capacity_match:
        sizes.append(f"{capacity_match.group(1)}kg")

    # Check for projection sizes
    if "projection_size" in specs:
        sizes.append(specs["projection_size"])

    return sizes


def generate_id(product_name: str, index: int) -> str:
    """Generate a unique ID for a product."""
    # Create slug from name
    slug = re.sub(r'[^a-z0-9]+', '-', product_name.lower())
    slug = slug.strip('-')[:30]
    return f"{slug}-{index:03d}"


class ProductDatabase:
    def __init__(self, json_path: str = None):
        if json_path is None:
            json_path = Path(__file__).parent / "sale_products.json"
        self.json_path = Path(json_path)
        self.products: list[Product] = []
        self._load_products()

    def _load_products(self) -> None:
        """Load products from Hisense scraped JSON file."""
        with open(self.json_path, "r") as f:
            data = json.load(f)

        raw_products = data.get("hisenseme_products", [])

        for i, p in enumerate(raw_products):
            name = p.get("product_name", f"Product {i}")
            specs = p.get("technical_specifications", {})

            # Extract features from key_features array
            features = []
            for feat in p.get("key_features", []):
                if isinstance(feat, dict):
                    features.append(feat.get("value", ""))
                elif isinstance(feat, str):
                    features.append(feat)

            # Detect category
            category = detect_category(name, specs)

            # Extract URL
            url = p.get("product_name_citation", None)

            # Extract available sizes
            sizes = extract_sizes(specs, name)

            product = Product(
                id=generate_id(name, i),
                name=name,
                category=category,
                brand="Hisense",
                specs=specs,
                features=features,
                url=url,
                sizes=sizes,
            )
            self.products.append(product)

        print(f"Loaded {len(self.products)} products from {self.json_path}")

        # Print category breakdown
        from collections import Counter
        categories = Counter(p.category.value for p in self.products)
        print(f"Categories: {dict(categories)}")

    def get_all_products(self) -> list[Product]:
        """Get all products."""
        return self.products

    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Get a single product by ID."""
        for product in self.products:
            if product.id == product_id:
                return product
        return None

    def get_products_by_category(self, category: ProductCategory) -> list[Product]:
        """Get all products in a category."""
        return [p for p in self.products if p.category == category]

    def filter_products(
        self,
        category: Optional[str] = None,
        brands: Optional[list[str]] = None,
    ) -> list[Product]:
        """Filter products based on criteria."""
        results = self.products

        if category:
            try:
                cat = ProductCategory(category.lower())
                results = [p for p in results if p.category == cat]
            except ValueError:
                pass  # Invalid category, don't filter

        if brands:
            brands_lower = [b.lower() for b in brands]
            results = [p for p in results if p.brand.lower() in brands_lower]

        return results

    def get_categories(self) -> list[str]:
        """Get list of available categories that have products."""
        available = set(p.category.value for p in self.products)
        return sorted(available)

    def get_brands(self, category: Optional[str] = None) -> list[str]:
        """Get list of brands, optionally filtered by category."""
        products = self.products
        if category:
            try:
                cat = ProductCategory(category.lower())
                products = [p for p in products if p.category == cat]
            except ValueError:
                pass
        return sorted(set(p.brand for p in products))

    def search_products(self, query: str) -> list[Product]:
        """Simple text search across product names, specs, and features."""
        query_lower = query.lower()
        results = []

        for product in self.products:
            # Search in name
            if query_lower in product.name.lower():
                results.append(product)
                continue

            # Search in specs
            specs_str = json.dumps(product.specs).lower()
            if query_lower in specs_str:
                results.append(product)
                continue

            # Search in features
            features_str = " ".join(product.features).lower()
            if query_lower in features_str:
                results.append(product)
                continue

        return results


# Singleton instance
_db: Optional[ProductDatabase] = None


def get_database() -> ProductDatabase:
    """Get the database singleton instance."""
    global _db
    if _db is None:
        _db = ProductDatabase()
    return _db
