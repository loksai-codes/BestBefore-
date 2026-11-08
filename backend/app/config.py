from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env", "../infra/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GROQ_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    BIFROST_BASE_URL: str = "http://localhost:8080"
    FALKORDB_HOST: Optional[str] = None
    FALKORDB_PORT: Optional[int] = None
    FALKORDB_USERNAME: Optional[str] = None
    FALKORDB_PASSWORD: Optional[str] = None
    FALKORDB_SSL: bool = True
    FALKORDB_GRAPH: str = "bestbefore"
    FALKORDB_GRAPH_TEST: str = "bestbefore_test"


settings = Settings()


class ScoringSettings(BaseModel):
    """Configurable weights and thresholds for deterministic freshness scoring."""

    # Authority weights for sources
    authority_weights: Dict[str, float] = {
        "official": 1.0,
        "reputable": 0.75,
        "community": 0.40,
        "unknown": 0.20,
    }
    supporting_evidence_weight: float = 2.5  # Multiplier for evidence agreeing with verdict

    # Half-life decay in days per volatility
    volatility_half_lives: Dict[str, int] = {
        "high": 30,
        "medium": 180,
        "low": 730,
    }
    unknown_date_recency: float = 0.40

    # Base formula component weights (sum = 1.00)
    base_weights: Dict[str, float] = {
        "authority": 0.30,
        "recency": 0.25,
        "agreement": 0.25,
        "confidence": 0.20,
    }

    # Conflict penalty factor in base * (1 - penalty_factor * conflict_penalty)
    penalty_factor: float = 0.50
    no_official_source_penalty: float = 0.35

    # Verdict score caps
    verdict_caps: Dict[str, int] = {
        "current": 100,
        "partially_outdated": 60,
        "outdated": 25,
        "unverifiable": 40,
        "skipped": 100,
    }

    # Volatility weights for overall freshness calculation
    volatility_weights: Dict[str, float] = {
        "high": 3.0,
        "medium": 2.0,
        "low": 1.0,
    }


scoring_settings = ScoringSettings()

# Search policies per claim type
SEARCH_POLICIES: Dict[str, Dict[str, Any]] = {
    "pricing": {
        "search_depth": "advanced",
        "topic": "general",
        "days": 90,
        "prefer_official": True,
    },
    "api_version": {
        "search_depth": "advanced",
        "topic": "general",
        "days": 180,
        "prefer_official": True,
    },
    "regulation": {
        "search_depth": "advanced",
        "topic": "general",
        "days": 180,
        "include_domains": [
            "europa.eu",
            "ftc.gov",
            "sec.gov",
            "federalregister.gov",
            "reuters.com",
        ],
        "prefer_official": True,
    },
    "leadership": {
        "search_depth": "advanced",
        "topic": "news",
        "days": 90,
        "prefer_official": True,
    },
    "product_release": {
        "search_depth": "advanced",
        "topic": "general",
        "days": 180,
        "prefer_official": True,
    },
    "other": {
        "search_depth": "basic",
        "topic": "general",
        "days": 365,
        "prefer_official": False,
    },
}

# Known entity domains for targeted domain filtering & authority classification
KNOWN_ENTITY_DOMAINS: Dict[str, str] = {
    "openai": "openai.com",
    "gpt-4": "openai.com",
    "gpt-4o": "openai.com",
    "gpt-3.5": "openai.com",
    "anthropic": "anthropic.com",
    "claude": "anthropic.com",
    "next.js": "nextjs.org",
    "nextjs": "nextjs.org",
    "react": "react.dev",
    "twitter": "x.com",
    "x": "x.com",
    "starbucks": "starbucks.com",
    "microsoft": "microsoft.com",
    "google": "google.com",
    "meta": "meta.com",
    "apple": "apple.com",
    "amazon": "amazon.com",
    "ftc": "ftc.gov",
    "sec": "sec.gov",
    "eu": "europa.eu",
    "european union": "europa.eu",
}
