import json
import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

from models import ParsedQuery
from prompts import (
    QUERY_PARSING_SYSTEM_PROMPT,
    get_query_parsing_prompt,
    RECOMMENDATION_SYSTEM_PROMPT,
    get_recommendation_prompt,
)

load_dotenv()


class AIService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"  # Cost-effective model, upgrade to gpt-4o for better accuracy

    def parse_query(self, query: str) -> ParsedQuery:
        """Parse a natural language query into structured filters."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": QUERY_PARSING_SYSTEM_PROMPT},
                    {"role": "user", "content": get_query_parsing_prompt(query)},
                ],
                temperature=0.1,  # Low temperature for consistent parsing
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()

            # Clean up potential markdown formatting
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            parsed_data = json.loads(content)
            return ParsedQuery(**parsed_data)

        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            # Return empty parsed query on failure
            return ParsedQuery()
        except Exception as e:
            print(f"AI parsing error: {e}")
            return ParsedQuery()

    def generate_recommendations(
        self,
        query: str,
        parsed_query: ParsedQuery,
        filtered_products: list[dict],
    ) -> dict:
        """Generate personalized recommendations with reasoning."""
        if not filtered_products:
            return {
                "message": "I couldn't find any products matching your requirements. Could you try adjusting your budget or requirements?",
                "recommendations": [],
            }

        try:
            # Limit to top 10 candidates to reduce token usage
            candidates = filtered_products[:10]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": get_recommendation_prompt(
                            query, parsed_query.model_dump(), candidates
                        ),
                    },
                ],
                temperature=0.7,  # Slightly higher for more natural responses
                max_tokens=1000,
            )

            content = response.choices[0].message.content.strip()

            # Clean up potential markdown formatting
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            print(f"Failed to parse recommendation response: {e}")
            # Fallback: return products without AI reasoning
            return {
                "message": "Here are some products that match your requirements:",
                "recommendations": [
                    {
                        "product_id": p["id"],
                        "score": 70,
                        "reasoning": f"{p['name']} - a solid choice in this category.",
                    }
                    for p in filtered_products[:5]
                ],
            }
        except Exception as e:
            print(f"AI recommendation error: {e}")
            return {
                "message": "Here are some products that might interest you:",
                "recommendations": [
                    {
                        "product_id": p["id"],
                        "score": 70,
                        "reasoning": f"{p['name']} by {p['brand']} at ₹{p['price']:,}",
                    }
                    for p in filtered_products[:5]
                ],
            }


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get the AI service singleton instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
