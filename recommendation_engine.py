import json
import re
from typing import Optional
from models import (
    ParsedQuery,
    Product,
    ProductRecommendation,
    RecommendationResponse,
    ProductCategory,
)
from database import get_database
from ai_service import get_ai_service


class RecommendationEngine:
    def __init__(self):
        self.db = get_database()
        self.ai = get_ai_service()

    def get_recommendations(self, query: str) -> RecommendationResponse:
        """Main entry point: process a query and return recommendations."""

        # Step 1: Parse the query using AI
        parsed_query = self.ai.parse_query(query)

        # Step 2: Filter products based on parsed criteria
        filtered_products = self._filter_products(parsed_query)

        # Step 3: Apply smart scoring based on requirements
        scored_products = self._score_products(filtered_products, parsed_query, query)

        # Sort by score (highest first) and take top candidates
        scored_products.sort(key=lambda x: x["score"], reverse=True)

        # Step 4: Generate AI recommendations with reasoning
        products_for_ai = [
            {
                "id": p["product"].id,
                "name": p["product"].name,
                "category": p["product"].category.value,
                "specs": p["product"].specs,
                "features": p["product"].features,
                "sizes": p["product"].sizes,
                "url": p["product"].url,
            }
            for p in scored_products[:10]
        ]

        ai_result = self.ai.generate_recommendations(query, parsed_query, products_for_ai)

        # Step 5: Build final response
        recommendations = []
        for rec in ai_result.get("recommendations", [])[:3]:
            product = self.db.get_product_by_id(rec["product_id"])
            if product:
                recommendations.append(
                    ProductRecommendation(
                        product=product,
                        score=rec.get("score", 70),
                        reasoning=rec.get("reasoning", ""),
                    )
                )

        return RecommendationResponse(
            query=query,
            parsed_query=parsed_query,
            recommendations=recommendations,
            message=ai_result.get("message", "Here are your recommendations:"),
        )

    def _filter_products(self, parsed: ParsedQuery) -> list[Product]:
        """Filter products based on parsed query criteria."""
        products = self.db.get_all_products()

        # Filter by category if specified
        if parsed.category:
            try:
                cat = ProductCategory(parsed.category.lower())
                products = [p for p in products if p.category == cat]
            except ValueError:
                pass  # Invalid category, don't filter

        return products

    def _score_products(
        self, products: list[Product], parsed: ParsedQuery, query: str
    ) -> list[dict]:
        """Score products based on how well they match requirements."""
        scored = []
        query_lower = query.lower()

        for product in products:
            score = 50  # Base score

            # Category match bonus
            if parsed.category:
                try:
                    cat = ProductCategory(parsed.category.lower())
                    if product.category == cat:
                        score += 15
                except ValueError:
                    pass

            # Keyword matching in product name
            keywords = parsed.keywords + parsed.must_have_features
            for keyword in keywords:
                if keyword.lower() in product.name.lower():
                    score += 10

            # Feature matching
            features_text = " ".join(product.features).lower()
            specs_text = json.dumps(product.specs).lower()

            for keyword in keywords:
                if keyword.lower() in features_text or keyword.lower() in specs_text:
                    score += 5

            # Query term matching
            query_terms = query_lower.split()
            for term in query_terms:
                if len(term) > 3:  # Skip short words
                    if term in product.name.lower():
                        score += 3
                    if term in features_text or term in specs_text:
                        score += 2

            # Size preference matching
            if parsed.size_preference:
                size_pref = parsed.size_preference.lower()
                if any(size_pref in s.lower() for s in product.sizes):
                    score += 15
                # Check in specs
                if size_pref in specs_text:
                    score += 10

            # Capacity matching
            if parsed.capacity:
                capacity = parsed.capacity.lower()
                if capacity in product.name.lower() or capacity in specs_text:
                    score += 15

            # Use case specific scoring
            score += self._use_case_score(product, parsed)

            scored.append({"product": product, "score": min(score, 100)})

        return scored

    def _use_case_score(self, product: Product, parsed: ParsedQuery) -> int:
        """Apply use-case specific scoring."""
        bonus = 0
        use_case = (parsed.use_case or "").lower()
        features_text = " ".join(product.features).lower()
        specs_text = json.dumps(product.specs).lower()

        if product.category == ProductCategory.TV:
            # Gaming use case
            if "gaming" in use_case or "game" in use_case:
                if "120hz" in specs_text or "144hz" in specs_text or "165hz" in specs_text:
                    bonus += 15
                if "game mode" in features_text or "game bar" in features_text:
                    bonus += 10
                if "vrr" in specs_text or "allm" in specs_text:
                    bonus += 5

            # Movies/cinema use case
            if "movie" in use_case or "cinema" in use_case:
                if "dolby vision" in specs_text or "dolby atmos" in features_text:
                    bonus += 15
                if "hdr" in specs_text:
                    bonus += 10
                if "oled" in specs_text or "miniled" in specs_text or "mini-led" in specs_text:
                    bonus += 10

            # Sports use case
            if "sport" in use_case:
                if "sports mode" in features_text or "ai sports" in features_text:
                    bonus += 15
                if "memc" in specs_text or "motion" in features_text:
                    bonus += 10

        elif product.category == ProductCategory.REFRIGERATOR:
            # Family size considerations
            if parsed.family_size:
                capacity_match = re.search(r'(\d+)\s*L', product.name, re.IGNORECASE)
                if capacity_match:
                    capacity = int(capacity_match.group(1))
                    ideal = parsed.family_size * 100  # ~100L per person
                    if abs(capacity - ideal) < 100:
                        bonus += 15
                    elif abs(capacity - ideal) < 200:
                        bonus += 10

        elif product.category == ProductCategory.WASHING_MACHINE:
            # Family size for washing machines
            if parsed.family_size:
                capacity_match = re.search(r'(\d+)\s*kg', product.name, re.IGNORECASE)
                if capacity_match:
                    capacity = int(capacity_match.group(1))
                    # ~2kg per person
                    ideal = parsed.family_size * 2
                    if abs(capacity - ideal) <= 2:
                        bonus += 15
                    elif abs(capacity - ideal) <= 4:
                        bonus += 10

            # Smart features
            if "smart" in use_case or "connected" in use_case:
                if "connect" in features_text or "app" in features_text:
                    bonus += 10

        elif product.category == ProductCategory.AC:
            # Room size considerations
            room_size = (parsed.room_size or "").lower()
            if "large" in room_size or "living" in room_size:
                if "2 ton" in specs_text or "24000" in specs_text:
                    bonus += 15
            elif "small" in room_size or "bedroom" in room_size:
                if "1 ton" in specs_text or "1.5 ton" in specs_text:
                    bonus += 15

            # Inverter preference
            if "inverter" in features_text or "inverter" in specs_text:
                bonus += 5

        elif product.category == ProductCategory.SOUNDBAR:
            # Dolby Atmos for movies
            if "movie" in use_case or "cinema" in use_case:
                if "dolby atmos" in features_text or "atmos" in specs_text:
                    bonus += 15

            # Subwoofer for bass
            if "bass" in use_case or "music" in use_case:
                if "subwoofer" in product.name.lower() or "subwoofer" in specs_text:
                    bonus += 10

        elif product.category == ProductCategory.PROJECTOR:
            # Home cinema
            if "cinema" in use_case or "movie" in use_case:
                if "laser" in product.name.lower() or "4k" in specs_text:
                    bonus += 15
                if "dolby" in specs_text:
                    bonus += 10

        return bonus


# Singleton instance
_engine: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    """Get the recommendation engine singleton instance."""
    global _engine
    if _engine is None:
        _engine = RecommendationEngine()
    return _engine
