# Kana Campaign Engine — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a multi-agent marketing platform where a user enters a company URL and gets a complete marketing package (research dossier, marketing profile, audience segments, content strategy, sales outreach, ad creatives) through 6 AI agents with human approval at every step.

**Architecture:** Sequential pipeline of 6 Python agent functions, each calling the Claude API with Pydantic-structured outputs. No framework (no LangGraph) — just the Anthropic SDK, FastAPI, and React. ChromaDB for shared context. Frontend is a step-by-step wizard that calls one backend endpoint per agent, waits for human approval, then calls the next.

**Tech Stack:** Python 3.11+ / FastAPI / Anthropic SDK / Tavily API / ChromaDB / React 18 / Tailwind CSS / Plotly.js / ElevenLabs API (optional) / Docker / Render

**Design doc:** `docs/plans/2026-02-21-kana-campaign-engine-design.md`

---

## Project Structure

```
kana-campaign-engine/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry
│   │   ├── config.py                  # Settings, API keys
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── dossier.py             # Research Scout output schema
│   │   │   ├── profile.py             # Marketing Profile schema
│   │   │   ├── audience.py            # Audience segments schema
│   │   │   ├── content.py             # Content strategy schema
│   │   │   ├── sales.py               # Sales pipeline schema
│   │   │   ├── ads.py                 # Ad creative schema
│   │   │   └── pipeline.py            # Pipeline state
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Base agent class
│   │   │   ├── research_scout.py      # Agent 0
│   │   │   ├── profile_creator.py     # Agent 1
│   │   │   ├── audience_identifier.py # Agent 2
│   │   │   ├── content_strategist.py  # Agent 3
│   │   │   ├── sales_agent.py         # Agent 4
│   │   │   └── ad_generator.py        # Agent 5
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm.py                 # Anthropic client wrapper
│   │   │   ├── tavily_client.py       # Tavily search + crawl + extract
│   │   │   ├── aeo_scorer.py          # AEO visibility scoring
│   │   │   ├── vdb.py                 # ChromaDB wrapper
│   │   │   └── image_gen.py           # Image generation (Phase 2)
│   │   └── api/
│   │       ├── __init__.py
│   │       └── routes.py              # FastAPI route handlers
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # Shared fixtures
│   │   ├── test_models.py
│   │   ├── test_services/
│   │   │   ├── __init__.py
│   │   │   ├── test_llm.py
│   │   │   ├── test_tavily_client.py
│   │   │   ├── test_aeo_scorer.py
│   │   │   └── test_vdb.py
│   │   └── test_agents/
│   │       ├── __init__.py
│   │       ├── test_research_scout.py
│   │       ├── test_profile_creator.py
│   │       ├── test_audience_identifier.py
│   │       └── test_content_strategist.py
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── index.css
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript types matching Pydantic models
│   │   ├── api/
│   │   │   └── client.ts             # API client functions
│   │   ├── components/
│   │   │   ├── Layout.tsx
│   │   │   ├── UrlInput.tsx
│   │   │   ├── StepWizard.tsx
│   │   │   ├── ApprovalGate.tsx
│   │   │   ├── DossierView.tsx
│   │   │   ├── ProfileView.tsx
│   │   │   ├── AudienceView.tsx
│   │   │   ├── ContentView.tsx
│   │   │   ├── SalesView.tsx
│   │   │   ├── AdsView.tsx
│   │   │   └── AeoScoreCard.tsx
│   │   └── hooks/
│   │       └── usePipeline.ts
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── index.html
├── docker-compose.yml
└── README.md
```

---

## Phase 1: Foundation (Tasks 1–4)

### Task 1: Project Scaffolding

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`
- Create: `backend/requirements.txt`, `backend/.env.example`
- Create: `backend/tests/__init__.py`, `backend/tests/conftest.py`

**Step 1: Create backend directory structure**

```bash
mkdir -p backend/app/models backend/app/agents backend/app/services backend/app/api
mkdir -p backend/tests/test_services backend/tests/test_agents
```

**Step 2: Write requirements.txt**

```
# backend/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
anthropic==0.43.0
tavily-python==0.5.0
chromadb==0.5.23
pydantic==2.10.0
pydantic-settings==2.7.0
python-dotenv==1.0.1
httpx==0.28.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

**Step 3: Write config.py**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    tavily_api_key: str
    openai_api_key: str = ""  # Optional, for AEO multi-LLM check
    elevenlabs_api_key: str = ""  # Optional, for voice agent
    chroma_persist_dir: str = "./chroma_data"
    claude_model: str = "claude-sonnet-4-5-20250929"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 4: Write main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Kana Campaign Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 5: Write .env.example**

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
```

**Step 6: Write conftest.py with shared fixtures**

```python
# backend/tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_anthropic_client():
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.parse = AsyncMock()
    return client

@pytest.fixture
def mock_tavily_client():
    client = MagicMock()
    client.crawl = MagicMock()
    client.search = MagicMock()
    client.extract = MagicMock()
    return client
```

**Step 7: Create all __init__.py files**

Empty `__init__.py` in every package directory.

**Step 8: Verify setup**

Run: `cd backend && pip install -r requirements.txt && python -c "from app.main import app; print('OK')"`
Expected: `OK`

**Step 9: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project structure with FastAPI"
```

---

### Task 2: Pydantic Models (All Agent Schemas)

**Files:**
- Create: `backend/app/models/__init__.py`, `dossier.py`, `profile.py`, `audience.py`, `content.py`, `sales.py`, `ads.py`, `pipeline.py`
- Test: `backend/tests/test_models.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_models.py
import pytest
from app.models.dossier import CompanyDossier, Competitor, AeoVisibility
from app.models.profile import MarketingProfile, BrandDna
from app.models.audience import AudienceSegments, Segment
from app.models.content import ContentStrategy, SocialPost, EmailCampaign
from app.models.sales import SalesPipeline, EmailSequence
from app.models.ads import AdCreatives, MetaAd
from app.models.pipeline import PipelineState, StepStatus


def test_company_dossier_valid():
    dossier = CompanyDossier(
        company_name="ToyBox Co",
        url="https://toybox.example.com",
        description="Eco-friendly baby toys",
        products_services=["Wooden blocks", "Fabric dolls"],
        value_propositions=["Safe materials", "Recycled packaging"],
        brand_voice_samples=["Fun meets responsibility"],
        target_market_signals=["Parents aged 25-35"],
        competitive_landscape=[
            Competitor(name="GreenToy", positioning="budget eco toys", strengths=["price"], weaknesses=["quality"])
        ],
        aeo_visibility=AeoVisibility(
            score=3,
            max_score=10,
            queries_tested=["best baby toys", "safe recycled toys"],
            results=[],
            gaps=["Not mentioned in GPT-4 responses"]
        ),
    )
    assert dossier.company_name == "ToyBox Co"
    assert dossier.aeo_visibility.score == 3


def test_marketing_profile_valid():
    profile = MarketingProfile(
        brand_dna=BrandDna(
            mission="Make play safe and sustainable",
            values=["safety", "sustainability"],
            tone="playful, trustworthy",
            visual_style="bright, natural"
        ),
        positioning_statement="For eco-conscious parents who want safe toys, ToyBox is the brand that combines recycled materials with sensory play.",
        usps=["100% recycled materials", "Sensory-active design"],
        competitive_advantages=["Only brand combining recycled + sensory"],
        identified_gaps=["No AEO presence", "No email marketing"],
        recommended_focus_areas=["Instagram + Pinterest", "Parenting blog SEO"],
    )
    assert len(profile.usps) == 2


def test_audience_segments_valid():
    segments = AudienceSegments(
        segments=[
            Segment(
                name="Eco-Conscious New Parents",
                demographics={"age": "25-35", "income": "60-100K"},
                psychographics=["values sustainability", "researches products"],
                pain_points=["worried about chemicals"],
                buying_triggers=["safety certifications"],
                channels=["Instagram", "Pinterest"],
                reasoning="Product aligns with eco-parenting values",
            )
        ]
    )
    assert len(segments.segments) == 1
    assert segments.segments[0].name == "Eco-Conscious New Parents"


def test_content_strategy_valid():
    strategy = ContentStrategy(
        social_posts=[
            SocialPost(
                segment="Eco-Conscious New Parents",
                platform="Instagram",
                post_type="carousel",
                copy="Safe play starts here...",
                hashtags=["#ecotoys", "#safebabytoys"],
                posting_time="Tuesday 9am EST",
            )
        ],
        email_campaigns=[
            EmailCampaign(
                segment="Eco-Conscious New Parents",
                subject_line="Why recycled toys matter",
                body="Dear parent...",
                cta="Shop Now",
            )
        ],
        blog_outlines=[],
    )
    assert strategy.social_posts[0].platform == "Instagram"


def test_pipeline_state_initial():
    state = PipelineState(company_url="https://example.com")
    assert state.current_step == StepStatus.URL_INPUT
    assert state.dossier is None


def test_pipeline_state_rejects_empty_url():
    with pytest.raises(Exception):
        PipelineState(company_url="")
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL — modules don't exist yet

**Step 3: Write all model files**

```python
# backend/app/models/__init__.py
from .dossier import CompanyDossier, Competitor, AeoVisibility
from .profile import MarketingProfile, BrandDna
from .audience import AudienceSegments, Segment
from .content import ContentStrategy, SocialPost, EmailCampaign
from .sales import SalesPipeline, EmailSequence
from .ads import AdCreatives, MetaAd
from .pipeline import PipelineState, StepStatus
```

```python
# backend/app/models/dossier.py
from pydantic import BaseModel

class Competitor(BaseModel):
    name: str
    positioning: str
    strengths: list[str]
    weaknesses: list[str]

class AeoResult(BaseModel):
    query: str
    llm: str
    mentioned: bool
    context: str = ""
    sentiment: str = ""

class AeoVisibility(BaseModel):
    score: int
    max_score: int = 10
    queries_tested: list[str]
    results: list[AeoResult] = []
    gaps: list[str] = []

class CompanyDossier(BaseModel):
    company_name: str
    url: str
    description: str
    products_services: list[str]
    value_propositions: list[str]
    brand_voice_samples: list[str] = []
    target_market_signals: list[str] = []
    competitive_landscape: list[Competitor] = []
    aeo_visibility: AeoVisibility | None = None
```

```python
# backend/app/models/profile.py
from pydantic import BaseModel

class BrandDna(BaseModel):
    mission: str
    values: list[str]
    tone: str
    visual_style: str

class MarketingProfile(BaseModel):
    brand_dna: BrandDna
    positioning_statement: str
    usps: list[str]
    competitive_advantages: list[str]
    identified_gaps: list[str]
    recommended_focus_areas: list[str]
```

```python
# backend/app/models/audience.py
from pydantic import BaseModel

class Segment(BaseModel):
    name: str
    demographics: dict[str, str]
    psychographics: list[str]
    pain_points: list[str]
    buying_triggers: list[str]
    channels: list[str]
    reasoning: str

class AudienceSegments(BaseModel):
    segments: list[Segment]
```

```python
# backend/app/models/content.py
from pydantic import BaseModel

class SocialPost(BaseModel):
    segment: str
    platform: str
    post_type: str
    copy: str
    hashtags: list[str] = []
    posting_time: str = ""

class EmailCampaign(BaseModel):
    segment: str
    subject_line: str
    body: str
    cta: str

class BlogOutline(BaseModel):
    title: str
    segment: str
    sections: list[str]

class ContentStrategy(BaseModel):
    social_posts: list[SocialPost]
    email_campaigns: list[EmailCampaign]
    blog_outlines: list[BlogOutline] = []
```

```python
# backend/app/models/sales.py
from pydantic import BaseModel

class EmailStep(BaseModel):
    day: int
    subject: str
    body: str

class EmailSequence(BaseModel):
    segment: str
    steps: list[EmailStep]

class LinkedInTemplate(BaseModel):
    segment: str
    message: str

class LeadScoring(BaseModel):
    criteria: list[str]
    scoring_rules: dict[str, int] = {}

class SalesPipeline(BaseModel):
    email_sequences: list[EmailSequence]
    linkedin_templates: list[LinkedInTemplate] = []
    lead_scoring: LeadScoring | None = None
    pipeline_stages: list[str] = ["prospect", "contacted", "engaged", "converted"]
    voice_agent_script: str | None = None
```

```python
# backend/app/models/ads.py
from pydantic import BaseModel

class MetaAd(BaseModel):
    segment: str
    primary_text: str
    headline: str
    description: str = ""
    image_prompt: str = ""
    image_url: str = ""
    ab_variant: str = "A"

class GoogleAd(BaseModel):
    segment: str
    headlines: list[str]
    descriptions: list[str]

class AdCreatives(BaseModel):
    meta_ads: list[MetaAd] = []
    google_ads: list[GoogleAd] = []
    generated_images: list[str] = []
```

```python
# backend/app/models/pipeline.py
from enum import Enum
from pydantic import BaseModel, field_validator
from .dossier import CompanyDossier
from .profile import MarketingProfile
from .audience import AudienceSegments
from .content import ContentStrategy
from .sales import SalesPipeline
from .ads import AdCreatives

class StepStatus(str, Enum):
    URL_INPUT = "url_input"
    RESEARCHING = "researching"
    RESEARCH_REVIEW = "research_review"
    PROFILING = "profiling"
    PROFILE_REVIEW = "profile_review"
    IDENTIFYING_AUDIENCE = "identifying_audience"
    AUDIENCE_REVIEW = "audience_review"
    CREATING_CONTENT = "creating_content"
    CONTENT_REVIEW = "content_review"
    GENERATING_SALES = "generating_sales"
    SALES_REVIEW = "sales_review"
    GENERATING_ADS = "generating_ads"
    ADS_REVIEW = "ads_review"
    COMPLETE = "complete"

class PipelineState(BaseModel):
    company_url: str
    current_step: StepStatus = StepStatus.URL_INPUT
    dossier: CompanyDossier | None = None
    profile: MarketingProfile | None = None
    audience: AudienceSegments | None = None
    content: ContentStrategy | None = None
    sales: SalesPipeline | None = None
    ads: AdCreatives | None = None

    @field_validator("company_url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("company_url cannot be empty")
        return v.strip()
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add Pydantic models for all agent input/output schemas"
```

---

### Task 3: Service Layer — LLM Client

**Files:**
- Create: `backend/app/services/__init__.py`, `backend/app/services/llm.py`
- Test: `backend/tests/test_services/test_llm.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_llm.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.llm import LLMService
from app.models.profile import MarketingProfile, BrandDna


def test_llm_service_parses_structured_output():
    """LLMService.generate() should return a parsed Pydantic model."""
    service = LLMService(api_key="test-key")

    mock_profile = MarketingProfile(
        brand_dna=BrandDna(mission="test", values=["v"], tone="t", visual_style="v"),
        positioning_statement="test",
        usps=["u"],
        competitive_advantages=["c"],
        identified_gaps=["g"],
        recommended_focus_areas=["r"],
    )

    with patch.object(service.client.messages, "parse") as mock_parse:
        mock_response = MagicMock()
        mock_response.parsed_output = mock_profile
        mock_parse.return_value = mock_response

        result = service.generate(
            system_prompt="You are a marketing expert.",
            user_prompt="Create a profile.",
            output_model=MarketingProfile,
        )

        assert isinstance(result, MarketingProfile)
        assert result.positioning_statement == "test"
        mock_parse.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_services/test_llm.py -v`
Expected: FAIL — module doesn't exist

**Step 3: Write LLM service**

```python
# backend/app/services/__init__.py
```

```python
# backend/app/services/llm.py
from typing import TypeVar, Type
import anthropic
from pydantic import BaseModel
from app.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMService:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or settings.anthropic_api_key)
        self.model = model or settings.claude_model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: Type[T],
        max_tokens: int = 4096,
    ) -> T:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_format=output_model,
        )
        return response.parsed_output

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_services/test_llm.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_services/
git commit -m "feat: add LLM service with structured output parsing"
```

---

### Task 4: Service Layer — Tavily Client + Web Crawler

**Files:**
- Create: `backend/app/services/tavily_client.py`
- Test: `backend/tests/test_services/test_tavily_client.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_tavily_client.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.tavily_client import TavilyService


def test_tavily_crawl_returns_pages():
    service = TavilyService(api_key="test-key")

    with patch.object(service.client, "crawl") as mock_crawl:
        mock_crawl.return_value = {
            "results": [
                {"url": "https://example.com", "raw_content": "Welcome to our site", "title": "Home"},
                {"url": "https://example.com/about", "raw_content": "About us", "title": "About"},
            ]
        }

        pages = service.crawl_website("https://example.com")
        assert len(pages) == 2
        assert pages[0]["url"] == "https://example.com"


def test_tavily_search_returns_results():
    service = TavilyService(api_key="test-key")

    with patch.object(service.client, "search") as mock_search:
        mock_search.return_value = {
            "results": [
                {"title": "Review", "url": "https://review.com", "content": "Great product"}
            ]
        }

        results = service.search("example company reviews")
        assert len(results) == 1
        assert "Great product" in results[0]["content"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_services/test_tavily_client.py -v`
Expected: FAIL

**Step 3: Write Tavily service**

```python
# backend/app/services/tavily_client.py
from tavily import TavilyClient
from app.config import settings


class TavilyService:
    def __init__(self, api_key: str | None = None):
        self.client = TavilyClient(api_key=api_key or settings.tavily_api_key)

    def crawl_website(self, url: str, max_depth: int = 2, limit: int = 15) -> list[dict]:
        response = self.client.crawl(
            url=url,
            max_depth=max_depth,
            limit=limit,
            format="markdown",
        )
        return response.get("results", [])

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        response = self.client.search(
            query=query,
            max_results=max_results,
            include_raw_content=False,
        )
        return response.get("results", [])

    def extract_urls(self, urls: list[str]) -> list[dict]:
        response = self.client.extract(
            urls=urls,
            format="markdown",
        )
        return response.get("results", [])
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_services/test_tavily_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/tavily_client.py backend/tests/test_services/test_tavily_client.py
git commit -m "feat: add Tavily service for web crawl, search, and extraction"
```

---

## Phase 2: Core Agents (Tasks 5–8)

### Task 5: Service Layer — AEO Scorer

**Files:**
- Create: `backend/app/services/aeo_scorer.py`
- Test: `backend/tests/test_services/test_aeo_scorer.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_aeo_scorer.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.aeo_scorer import AeoScorer
from app.models.dossier import AeoVisibility


def test_aeo_scorer_returns_visibility():
    scorer = AeoScorer(anthropic_key="test", openai_key="test")

    # Mock both LLM clients
    with patch.object(scorer, "_query_claude", return_value="I recommend BrandX for baby toys. Also check BrandY."):
        with patch.object(scorer, "_query_openai", return_value="The best baby toys are from TestCompany and others."):
            result = scorer.score(
                company_name="TestCompany",
                product_category="baby toys",
                queries=["best baby toys", "safe recycled toys"],
            )

            assert isinstance(result, AeoVisibility)
            assert result.max_score == 10
            assert isinstance(result.score, int)
            assert len(result.queries_tested) == 2
```

**Step 2: Run test — FAIL**

**Step 3: Write AEO scorer**

```python
# backend/app/services/aeo_scorer.py
import anthropic
from app.config import settings
from app.models.dossier import AeoVisibility, AeoResult


class AeoScorer:
    def __init__(self, anthropic_key: str | None = None, openai_key: str | None = None):
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key or settings.anthropic_api_key)
        self.openai_key = openai_key or settings.openai_api_key

    def _query_claude(self, query: str) -> str:
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": query}],
        )
        return response.content[0].text

    def _query_openai(self, query: str) -> str:
        if not self.openai_key:
            return ""
        import httpx
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.openai_key}"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 1024,
            },
            timeout=30,
        )
        return resp.json()["choices"][0]["message"]["content"]

    def score(
        self,
        company_name: str,
        product_category: str,
        queries: list[str] | None = None,
    ) -> AeoVisibility:
        if queries is None:
            queries = [
                f"What is the best {product_category}?",
                f"Recommend me a good {product_category}",
                f"What is {company_name}?",
                f"Top {product_category} brands",
                f"Which {product_category} should I buy?",
            ]

        results: list[AeoResult] = []
        mentions = 0
        company_lower = company_name.lower()

        for query in queries:
            for llm_name, query_fn in [("Claude", self._query_claude), ("GPT-4", self._query_openai)]:
                try:
                    answer = query_fn(query)
                    mentioned = company_lower in answer.lower()
                    if mentioned:
                        mentions += 1
                    results.append(AeoResult(
                        query=query,
                        llm=llm_name,
                        mentioned=mentioned,
                        context=answer[:300],
                    ))
                except Exception:
                    results.append(AeoResult(query=query, llm=llm_name, mentioned=False, context="Error"))

        total_checks = len(results) if results else 1
        score = round((mentions / total_checks) * 10)

        gaps = []
        if score < 3:
            gaps.append(f"{company_name} is largely invisible to AI chatbots")
        for llm in ["Claude", "GPT-4"]:
            llm_results = [r for r in results if r.llm == llm]
            llm_mentions = sum(1 for r in llm_results if r.mentioned)
            if llm_mentions == 0:
                gaps.append(f"Zero mentions in {llm} responses")

        return AeoVisibility(
            score=score,
            max_score=10,
            queries_tested=queries,
            results=results,
            gaps=gaps,
        )
```

**Step 4: Run test — PASS**

**Step 5: Commit**

```bash
git add backend/app/services/aeo_scorer.py backend/tests/test_services/test_aeo_scorer.py
git commit -m "feat: add AEO visibility scorer with multi-LLM querying"
```

---

### Task 6: Service Layer — ChromaDB (VDB)

**Files:**
- Create: `backend/app/services/vdb.py`
- Test: `backend/tests/test_services/test_vdb.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_vdb.py
import pytest
import tempfile
from app.services.vdb import VectorStore


@pytest.fixture
def vdb(tmp_path):
    return VectorStore(persist_dir=str(tmp_path / "test_chroma"))


def test_store_and_retrieve(vdb):
    vdb.store(
        collection="test",
        doc_id="doc1",
        text="This is a test document about baby toys",
        metadata={"agent": "research_scout", "company": "ToyBox"},
    )
    results = vdb.query(collection="test", query_text="baby toys", n_results=1)
    assert len(results) == 1
    assert "baby toys" in results[0]["text"]


def test_store_json(vdb):
    data = {"name": "ToyBox", "products": ["blocks", "dolls"]}
    vdb.store_json(collection="dossiers", doc_id="toybox", data=data)
    results = vdb.get_json(collection="dossiers", doc_id="toybox")
    assert results["name"] == "ToyBox"
```

**Step 2: Run test — FAIL**

**Step 3: Write VDB service**

```python
# backend/app/services/vdb.py
import json
import chromadb
from app.config import settings


class VectorStore:
    def __init__(self, persist_dir: str | None = None):
        self.client = chromadb.PersistentClient(
            path=persist_dir or settings.chroma_persist_dir
        )

    def _get_collection(self, name: str):
        return self.client.get_or_create_collection(name=name)

    def store(self, collection: str, doc_id: str, text: str, metadata: dict | None = None):
        coll = self._get_collection(collection)
        coll.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )

    def query(self, collection: str, query_text: str, n_results: int = 5) -> list[dict]:
        coll = self._get_collection(collection)
        results = coll.query(query_texts=[query_text], n_results=n_results)
        output = []
        for i, doc in enumerate(results["documents"][0]):
            output.append({
                "text": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "id": results["ids"][0][i],
            })
        return output

    def store_json(self, collection: str, doc_id: str, data: dict):
        text = json.dumps(data)
        self.store(collection, doc_id, text, metadata={"type": "json"})

    def get_json(self, collection: str, doc_id: str) -> dict | None:
        coll = self._get_collection(collection)
        result = coll.get(ids=[doc_id])
        if result["documents"] and result["documents"][0]:
            return json.loads(result["documents"][0])
        return None
```

**Step 4: Run test — PASS**

**Step 5: Commit**

```bash
git add backend/app/services/vdb.py backend/tests/test_services/test_vdb.py
git commit -m "feat: add ChromaDB vector store service"
```

---

### Task 7: Agent 0 — Research Scout

**Files:**
- Create: `backend/app/agents/__init__.py`, `backend/app/agents/base.py`, `backend/app/agents/research_scout.py`
- Test: `backend/tests/test_agents/test_research_scout.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_agents/test_research_scout.py
import pytest
from unittest.mock import MagicMock, patch
from app.agents.research_scout import ResearchScoutAgent
from app.models.dossier import CompanyDossier, AeoVisibility


@pytest.fixture
def mock_services():
    return {
        "llm": MagicMock(),
        "tavily": MagicMock(),
        "aeo": MagicMock(),
        "vdb": MagicMock(),
    }


def test_research_scout_produces_dossier(mock_services):
    # Mock tavily crawl
    mock_services["tavily"].crawl_website.return_value = [
        {"url": "https://toybox.com", "raw_content": "We make safe recycled baby toys.", "title": "Home"},
        {"url": "https://toybox.com/about", "raw_content": "Founded in 2023, eco-friendly.", "title": "About"},
    ]

    # Mock tavily search
    mock_services["tavily"].search.return_value = [
        {"title": "ToyBox Review", "content": "Great eco toys", "url": "https://review.com/toybox"},
    ]

    # Mock AEO scoring
    mock_services["aeo"].score.return_value = AeoVisibility(
        score=2, max_score=10, queries_tested=["best baby toys"], results=[], gaps=["Low visibility"]
    )

    # Mock LLM synthesis
    mock_dossier = CompanyDossier(
        company_name="ToyBox",
        url="https://toybox.com",
        description="Eco-friendly baby toy company",
        products_services=["Wooden blocks", "Fabric dolls"],
        value_propositions=["Safe recycled materials"],
        aeo_visibility=AeoVisibility(score=2, max_score=10, queries_tested=[], results=[], gaps=[]),
    )
    mock_services["llm"].generate.return_value = mock_dossier

    agent = ResearchScoutAgent(**mock_services)
    result = agent.run("https://toybox.com")

    assert isinstance(result, CompanyDossier)
    assert result.company_name == "ToyBox"
    mock_services["tavily"].crawl_website.assert_called_once_with("https://toybox.com")
    mock_services["vdb"].store_json.assert_called_once()
```

**Step 2: Run test — FAIL**

**Step 3: Write base agent and Research Scout**

```python
# backend/app/agents/__init__.py
```

```python
# backend/app/agents/base.py
from app.services.llm import LLMService
from app.services.vdb import VectorStore


class BaseAgent:
    """Base class for all agents. Holds references to shared services."""

    def __init__(self, llm: LLMService, vdb: VectorStore, **kwargs):
        self.llm = llm
        self.vdb = vdb
```

```python
# backend/app/agents/research_scout.py
from app.agents.base import BaseAgent
from app.services.llm import LLMService
from app.services.tavily_client import TavilyService
from app.services.aeo_scorer import AeoScorer
from app.services.vdb import VectorStore
from app.models.dossier import CompanyDossier

SYSTEM_PROMPT = """You are a marketing research analyst. Given crawled website content and external research about a company, produce a structured Company Intelligence Dossier.

Extract:
- Company name and description
- Products/services offered
- Value propositions and differentiators
- Brand voice samples (direct quotes from their copy)
- Target market signals (who they seem to be selling to)
- Competitive landscape (competitors mentioned or implied)

Be thorough but factual. Only include what the data supports."""


class ResearchScoutAgent(BaseAgent):
    def __init__(self, llm: LLMService, tavily: TavilyService, aeo: AeoScorer, vdb: VectorStore):
        super().__init__(llm=llm, vdb=vdb)
        self.tavily = tavily
        self.aeo = aeo

    def run(self, url: str) -> CompanyDossier:
        # Step 1: Crawl the website
        pages = self.tavily.crawl_website(url)
        crawled_content = "\n\n---\n\n".join(
            f"## {p.get('title', 'Page')}\nURL: {p['url']}\n\n{p['raw_content'][:3000]}"
            for p in pages
        )

        # Step 2: External search
        company_hint = pages[0].get("title", url) if pages else url
        search_results = self.tavily.search(f"{company_hint} company reviews press coverage")
        external_content = "\n".join(
            f"- {r['title']}: {r['content'][:500]}" for r in search_results
        )

        # Step 3: AEO scoring (extract product category from crawled content)
        category_prompt = f"Based on this website content, what is the primary product/service category in 3-5 words?\n\n{crawled_content[:2000]}"
        product_category = self.llm.generate_text(
            system_prompt="Extract the product category. Reply with just the category, nothing else.",
            user_prompt=category_prompt,
            max_tokens=50,
        ).strip()

        aeo_result = self.aeo.score(
            company_name=company_hint,
            product_category=product_category,
        )

        # Step 4: Synthesize into dossier via LLM
        user_prompt = f"""Analyze the following data and create a Company Intelligence Dossier.

## Website Content (Crawled)
{crawled_content[:8000]}

## External Research
{external_content[:3000]}

## AEO Visibility
Score: {aeo_result.score}/10
Gaps: {', '.join(aeo_result.gaps) if aeo_result.gaps else 'None identified'}

The company URL is: {url}"""

        dossier = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_model=CompanyDossier,
        )

        # Attach AEO results (LLM doesn't have the raw results)
        dossier.aeo_visibility = aeo_result

        # Step 5: Store in VDB
        self.vdb.store_json(
            collection="company_research",
            doc_id=url,
            data=dossier.model_dump(),
        )

        return dossier
```

**Step 4: Run test — PASS**

**Step 5: Commit**

```bash
git add backend/app/agents/ backend/tests/test_agents/
git commit -m "feat: add Research Scout agent with Tavily crawl + AEO scoring"
```

---

### Task 8: Agents 1–3 (Profile, Audience, Content)

**Files:**
- Create: `backend/app/agents/profile_creator.py`, `audience_identifier.py`, `content_strategist.py`
- Test: `backend/tests/test_agents/test_profile_creator.py`, `test_audience_identifier.py`, `test_content_strategist.py`

These agents follow the same pattern: read context from VDB/input, call LLM with a system prompt, return structured Pydantic output. I'll show Agent 1 in detail; Agents 2–3 follow the identical pattern with different prompts and output models.

**Step 1: Write failing tests for all three**

```python
# backend/tests/test_agents/test_profile_creator.py
import pytest
from unittest.mock import MagicMock
from app.agents.profile_creator import ProfileCreatorAgent
from app.models.profile import MarketingProfile, BrandDna
from app.models.dossier import CompanyDossier


def test_profile_creator_produces_profile():
    mock_llm = MagicMock()
    mock_vdb = MagicMock()

    expected = MarketingProfile(
        brand_dna=BrandDna(mission="Safe play", values=["safety"], tone="playful", visual_style="bright"),
        positioning_statement="For parents who care...",
        usps=["Recycled materials"],
        competitive_advantages=["Only recycled+sensory brand"],
        identified_gaps=["No AEO presence"],
        recommended_focus_areas=["Instagram"],
    )
    mock_llm.generate.return_value = expected

    dossier = CompanyDossier(
        company_name="ToyBox", url="https://toybox.com",
        description="Eco toys", products_services=["blocks"], value_propositions=["safe"],
    )

    agent = ProfileCreatorAgent(llm=mock_llm, vdb=mock_vdb)
    result = agent.run(dossier)

    assert isinstance(result, MarketingProfile)
    assert result.positioning_statement == "For parents who care..."
    mock_vdb.store_json.assert_called_once()
```

```python
# backend/tests/test_agents/test_audience_identifier.py
import pytest
from unittest.mock import MagicMock
from app.agents.audience_identifier import AudienceIdentifierAgent
from app.models.audience import AudienceSegments, Segment
from app.models.dossier import CompanyDossier
from app.models.profile import MarketingProfile, BrandDna


def test_audience_identifier_produces_segments():
    mock_llm = MagicMock()
    mock_vdb = MagicMock()

    expected = AudienceSegments(segments=[
        Segment(name="Eco Parents", demographics={"age": "25-35"},
                psychographics=["eco-conscious"], pain_points=["chemical fears"],
                buying_triggers=["certifications"], channels=["Instagram"],
                reasoning="Product targets eco-conscious parents")
    ])
    mock_llm.generate.return_value = expected

    dossier = CompanyDossier(
        company_name="ToyBox", url="https://toybox.com",
        description="Eco toys", products_services=["blocks"], value_propositions=["safe"],
    )
    profile = MarketingProfile(
        brand_dna=BrandDna(mission="m", values=["v"], tone="t", visual_style="vs"),
        positioning_statement="p", usps=["u"], competitive_advantages=["c"],
        identified_gaps=["g"], recommended_focus_areas=["r"],
    )

    agent = AudienceIdentifierAgent(llm=mock_llm, vdb=mock_vdb)
    result = agent.run(dossier, profile)

    assert len(result.segments) == 1
    assert result.segments[0].name == "Eco Parents"
```

```python
# backend/tests/test_agents/test_content_strategist.py
import pytest
from unittest.mock import MagicMock
from app.agents.content_strategist import ContentStrategistAgent
from app.models.content import ContentStrategy, SocialPost, EmailCampaign
from app.models.audience import AudienceSegments, Segment
from app.models.profile import MarketingProfile, BrandDna


def test_content_strategist_produces_strategy():
    mock_llm = MagicMock()
    mock_vdb = MagicMock()

    expected = ContentStrategy(
        social_posts=[SocialPost(segment="Eco Parents", platform="Instagram",
                                  post_type="carousel", copy="Safe play starts here")],
        email_campaigns=[EmailCampaign(segment="Eco Parents",
                                        subject_line="Why recycled?", body="Dear...", cta="Shop")],
    )
    mock_llm.generate.return_value = expected

    profile = MarketingProfile(
        brand_dna=BrandDna(mission="m", values=["v"], tone="t", visual_style="vs"),
        positioning_statement="p", usps=["u"], competitive_advantages=["c"],
        identified_gaps=["g"], recommended_focus_areas=["r"],
    )
    audience = AudienceSegments(segments=[
        Segment(name="Eco Parents", demographics={"age": "25-35"},
                psychographics=["eco"], pain_points=["chemicals"],
                buying_triggers=["certs"], channels=["Instagram"],
                reasoning="reason")
    ])

    agent = ContentStrategistAgent(llm=mock_llm, vdb=mock_vdb)
    result = agent.run(profile, audience)

    assert len(result.social_posts) == 1
    assert result.social_posts[0].platform == "Instagram"
```

**Step 2: Run tests — all FAIL**

**Step 3: Write all three agents**

```python
# backend/app/agents/profile_creator.py
from app.agents.base import BaseAgent
from app.models.dossier import CompanyDossier
from app.models.profile import MarketingProfile

SYSTEM_PROMPT = """You are a senior marketing strategist. Given a Company Intelligence Dossier, create a Marketing Profile that defines the brand's DNA, positioning, USPs, competitive advantages, gaps, and focus areas.

Be specific and actionable. The positioning statement should follow the format:
"For [target] who [need], [company] is the [category] that [differentiation] because [reason]."

Identify concrete gaps (e.g., "no email marketing", "zero AEO presence") and recommend specific focus areas."""


class ProfileCreatorAgent(BaseAgent):
    def run(self, dossier: CompanyDossier) -> MarketingProfile:
        user_prompt = f"""Create a Marketing Profile for this company:

{dossier.model_dump_json(indent=2)}"""

        profile = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_model=MarketingProfile,
        )

        self.vdb.store_json(
            collection="marketing_profiles",
            doc_id=dossier.url,
            data=profile.model_dump(),
        )

        return profile
```

```python
# backend/app/agents/audience_identifier.py
from app.agents.base import BaseAgent
from app.models.dossier import CompanyDossier
from app.models.profile import MarketingProfile
from app.models.audience import AudienceSegments

SYSTEM_PROMPT = """You are an audience research specialist. Given a company's dossier and marketing profile, identify 3-5 target customer segments.

For each segment provide:
- A descriptive name
- Demographics (age, income, location, etc.)
- Psychographics (values, interests, lifestyle)
- Pain points this product solves for them
- Buying triggers that would make them purchase
- Channels where they're most active (social platforms, forums, etc.)
- Clear reasoning for why this segment is a good fit

Be specific. "Women 25-45" is too broad. "Eco-conscious first-time mothers in urban areas who research products extensively before buying" is the right level of specificity."""


class AudienceIdentifierAgent(BaseAgent):
    def run(self, dossier: CompanyDossier, profile: MarketingProfile) -> AudienceSegments:
        user_prompt = f"""Identify target audience segments for this company.

## Company Dossier
{dossier.model_dump_json(indent=2)}

## Marketing Profile
{profile.model_dump_json(indent=2)}"""

        audience = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_model=AudienceSegments,
        )

        self.vdb.store_json(
            collection="audience_segments",
            doc_id=dossier.url,
            data=audience.model_dump(),
        )

        return audience
```

```python
# backend/app/agents/content_strategist.py
from app.agents.base import BaseAgent
from app.models.profile import MarketingProfile
from app.models.audience import AudienceSegments
from app.models.content import ContentStrategy

SYSTEM_PROMPT = """You are a content marketing expert. Given a marketing profile and audience segments, create a content strategy with actual draft content.

For each audience segment, generate:
- 3-5 social media posts (with platform, post type, copy, hashtags, ideal posting time)
- 1-2 email campaigns (subject line, body, CTA)
- 1 blog post outline if relevant

Match the brand's tone and visual style. Target each piece of content to a specific segment on a specific channel. Include hashtag suggestions and optimal posting times.

Write actual copy, not placeholders. The posts should be ready to publish."""


class ContentStrategistAgent(BaseAgent):
    def run(self, profile: MarketingProfile, audience: AudienceSegments) -> ContentStrategy:
        user_prompt = f"""Create a content strategy with draft content.

## Marketing Profile
{profile.model_dump_json(indent=2)}

## Audience Segments
{audience.model_dump_json(indent=2)}"""

        content = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_model=ContentStrategy,
            max_tokens=8192,
        )

        self.vdb.store_json(
            collection="content_assets",
            doc_id="latest",
            data=content.model_dump(),
        )

        return content
```

**Step 4: Run all agent tests — PASS**

Run: `cd backend && python -m pytest tests/test_agents/ -v`
Expected: All 4 agent tests PASS

**Step 5: Commit**

```bash
git add backend/app/agents/ backend/tests/test_agents/
git commit -m "feat: add Profile Creator, Audience Identifier, and Content Strategist agents"
```

---

## Phase 3: API + Frontend (Tasks 9–11)

### Task 9: FastAPI Routes

**Files:**
- Create: `backend/app/api/__init__.py`, `backend/app/api/routes.py`
- Modify: `backend/app/main.py` (add router)

**Step 1: Write routes**

```python
# backend/app/api/__init__.py
```

```python
# backend/app/api/routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm import LLMService
from app.services.tavily_client import TavilyService
from app.services.aeo_scorer import AeoScorer
from app.services.vdb import VectorStore
from app.agents.research_scout import ResearchScoutAgent
from app.agents.profile_creator import ProfileCreatorAgent
from app.agents.audience_identifier import AudienceIdentifierAgent
from app.agents.content_strategist import ContentStrategistAgent
from app.models.dossier import CompanyDossier
from app.models.profile import MarketingProfile
from app.models.audience import AudienceSegments
from app.models.content import ContentStrategy

router = APIRouter(prefix="/api")

# Shared service instances
llm = LLMService()
tavily = TavilyService()
aeo = AeoScorer()
vdb = VectorStore()


class UrlInput(BaseModel):
    url: str


@router.post("/research", response_model=CompanyDossier)
def run_research(input: UrlInput):
    agent = ResearchScoutAgent(llm=llm, tavily=tavily, aeo=aeo, vdb=vdb)
    return agent.run(input.url)


@router.post("/profile", response_model=MarketingProfile)
def run_profile(dossier: CompanyDossier):
    agent = ProfileCreatorAgent(llm=llm, vdb=vdb)
    return agent.run(dossier)


@router.post("/audience", response_model=AudienceSegments)
def run_audience(payload: dict):
    dossier = CompanyDossier(**payload["dossier"])
    profile = MarketingProfile(**payload["profile"])
    agent = AudienceIdentifierAgent(llm=llm, vdb=vdb)
    return agent.run(dossier, profile)


@router.post("/content", response_model=ContentStrategy)
def run_content(payload: dict):
    profile = MarketingProfile(**payload["profile"])
    audience = AudienceSegments(**payload["audience"])
    agent = ContentStrategistAgent(llm=llm, vdb=vdb)
    return agent.run(profile, audience)
```

**Step 2: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.api.routes import router
app.include_router(router)
```

**Step 3: Manual test**

Run: `cd backend && uvicorn app.main:app --reload`
Test: `curl http://localhost:8000/health` → `{"status": "ok"}`

**Step 4: Commit**

```bash
git add backend/app/api/ backend/app/main.py
git commit -m "feat: add FastAPI routes for research, profile, audience, content agents"
```

---

### Task 10: React Frontend Scaffolding

**Files:**
- Create: entire `frontend/` directory via Vite

**Step 1: Scaffold React + Tailwind project**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss @tailwindcss/vite
```

**Step 2: Configure Tailwind**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
```

```css
/* frontend/src/index.css */
@import "tailwindcss";
```

**Step 3: Write TypeScript types matching Pydantic models**

```typescript
// frontend/src/types/index.ts
export interface Competitor {
  name: string;
  positioning: string;
  strengths: string[];
  weaknesses: string[];
}

export interface AeoResult {
  query: string;
  llm: string;
  mentioned: boolean;
  context: string;
}

export interface AeoVisibility {
  score: number;
  max_score: number;
  queries_tested: string[];
  results: AeoResult[];
  gaps: string[];
}

export interface CompanyDossier {
  company_name: string;
  url: string;
  description: string;
  products_services: string[];
  value_propositions: string[];
  brand_voice_samples: string[];
  target_market_signals: string[];
  competitive_landscape: Competitor[];
  aeo_visibility: AeoVisibility | null;
}

export interface BrandDna {
  mission: string;
  values: string[];
  tone: string;
  visual_style: string;
}

export interface MarketingProfile {
  brand_dna: BrandDna;
  positioning_statement: string;
  usps: string[];
  competitive_advantages: string[];
  identified_gaps: string[];
  recommended_focus_areas: string[];
}

export interface Segment {
  name: string;
  demographics: Record<string, string>;
  psychographics: string[];
  pain_points: string[];
  buying_triggers: string[];
  channels: string[];
  reasoning: string;
}

export interface AudienceSegments {
  segments: Segment[];
}

export interface SocialPost {
  segment: string;
  platform: string;
  post_type: string;
  copy: string;
  hashtags: string[];
  posting_time: string;
}

export interface EmailCampaign {
  segment: string;
  subject_line: string;
  body: string;
  cta: string;
}

export interface ContentStrategy {
  social_posts: SocialPost[];
  email_campaigns: EmailCampaign[];
  blog_outlines: any[];
}

export type PipelineStep =
  | 'url_input'
  | 'researching' | 'research_review'
  | 'profiling' | 'profile_review'
  | 'identifying_audience' | 'audience_review'
  | 'creating_content' | 'content_review'
  | 'complete';
```

**Step 4: Write API client**

```typescript
// frontend/src/api/client.ts
import type { CompanyDossier, MarketingProfile, AudienceSegments, ContentStrategy } from '../types';

const BASE = '/api';

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  research: (url: string) => post<CompanyDossier>('/research', { url }),
  profile: (dossier: CompanyDossier) => post<MarketingProfile>('/profile', dossier),
  audience: (dossier: CompanyDossier, profile: MarketingProfile) =>
    post<AudienceSegments>('/audience', { dossier, profile }),
  content: (profile: MarketingProfile, audience: AudienceSegments) =>
    post<ContentStrategy>('/content', { profile, audience }),
};
```

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React frontend with TypeScript types and API client"
```

---

### Task 11: React Wizard UI (Core Pipeline)

**Files:**
- Create: `frontend/src/App.tsx`, `components/UrlInput.tsx`, `StepWizard.tsx`, `ApprovalGate.tsx`, `DossierView.tsx`, `ProfileView.tsx`, `AudienceView.tsx`, `ContentView.tsx`, `AeoScoreCard.tsx`, `hooks/usePipeline.ts`

This is the largest frontend task. The key components:

1. **`usePipeline` hook** — manages pipeline state, calls API endpoints sequentially
2. **`StepWizard`** — renders the current step with progress bar
3. **`ApprovalGate`** — approve/edit/reject buttons shown after each agent completes
4. **View components** — render each agent's output (DossierView, ProfileView, etc.)

**Step 1: Write the usePipeline hook**

```typescript
// frontend/src/hooks/usePipeline.ts
import { useState, useCallback } from 'react';
import { api } from '../api/client';
import type {
  PipelineStep, CompanyDossier, MarketingProfile,
  AudienceSegments, ContentStrategy
} from '../types';

interface PipelineData {
  dossier: CompanyDossier | null;
  profile: MarketingProfile | null;
  audience: AudienceSegments | null;
  content: ContentStrategy | null;
}

export function usePipeline() {
  const [step, setStep] = useState<PipelineStep>('url_input');
  const [data, setData] = useState<PipelineData>({
    dossier: null, profile: null, audience: null, content: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startResearch = useCallback(async (url: string) => {
    setStep('researching');
    setLoading(true);
    setError(null);
    try {
      const dossier = await api.research(url);
      setData(prev => ({ ...prev, dossier }));
      setStep('research_review');
    } catch (e: any) {
      setError(e.message);
      setStep('url_input');
    } finally {
      setLoading(false);
    }
  }, []);

  const approveResearch = useCallback(async (dossier: CompanyDossier) => {
    setData(prev => ({ ...prev, dossier }));
    setStep('profiling');
    setLoading(true);
    try {
      const profile = await api.profile(dossier);
      setData(prev => ({ ...prev, profile }));
      setStep('profile_review');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const approveProfile = useCallback(async (profile: MarketingProfile) => {
    setData(prev => ({ ...prev, profile }));
    setStep('identifying_audience');
    setLoading(true);
    try {
      const audience = await api.audience(data.dossier!, profile);
      setData(prev => ({ ...prev, audience }));
      setStep('audience_review');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [data.dossier]);

  const approveAudience = useCallback(async (audience: AudienceSegments) => {
    setData(prev => ({ ...prev, audience }));
    setStep('creating_content');
    setLoading(true);
    try {
      const content = await api.content(data.profile!, audience);
      setData(prev => ({ ...prev, content }));
      setStep('content_review');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [data.profile]);

  const approveContent = useCallback(async () => {
    setStep('complete');
  }, []);

  return {
    step, data, loading, error,
    startResearch, approveResearch, approveProfile,
    approveAudience, approveContent,
  };
}
```

**Step 2: Write the main App and view components**

The App.tsx renders a StepWizard that shows the appropriate view based on current step. Each view component (DossierView, ProfileView, etc.) renders the agent output as cards with an ApprovalGate at the bottom.

These are standard React components with Tailwind styling. The key UI pattern is:
- Loading state → spinner with "Agent is thinking..." message
- Review state → rendered output + Approve/Edit buttons
- The AeoScoreCard is a highlighted component showing the visibility score as a gauge

**Full component code will be written during implementation.** The patterns are:
- `UrlInput`: single input field + submit button
- `DossierView`: cards for company info, products, competitors, AEO score
- `ProfileView`: brand DNA card, positioning statement, gaps list
- `AudienceView`: segment cards with expand/collapse
- `ContentView`: tabbed view (social posts / emails / blog) with platform previews
- `ApprovalGate`: Approve (green) / Edit (yellow) / Retry (red) buttons

**Step 3: Verify dev server**

Run: `cd frontend && npm run dev`
Expected: App loads at `http://localhost:5173` with URL input

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add React wizard UI with pipeline hook and view components"
```

---

## Phase 4: Integration + Sales + Ads (Tasks 12–14)

### Task 12: End-to-End Integration Test

**Step 1:** Run backend: `cd backend && uvicorn app.main:app --reload`
**Step 2:** Run frontend: `cd frontend && npm run dev`
**Step 3:** Enter a real URL, verify the full pipeline works through content strategy
**Step 4:** Fix any issues found during integration
**Step 5:** Commit fixes

---

### Task 13: Agent 4 — Sales Agent + ElevenLabs (Nice-to-Have)

**Files:**
- Create: `backend/app/agents/sales_agent.py`
- Create: `backend/app/services/elevenlabs.py` (optional)

Same agent pattern as Tasks 7-8. The Sales Agent:
1. Takes audience + profile + content from VDB
2. Generates email sequences, LinkedIn templates, lead scoring via Claude
3. Optionally creates an ElevenLabs voice agent with the product knowledge

Refer to design doc `Agent 4: Sales Agent` section for full specification.

---

### Task 14: Agent 5 — Ad Creative Generator (Should-Have)

**Files:**
- Create: `backend/app/agents/ad_generator.py`
- Create: `backend/app/services/image_gen.py`

Same agent pattern. The Ad Generator:
1. Takes profile + audience + content from VDB
2. Generates ad copy per platform via Claude
3. Generates images via Replicate (Flux) or DALL-E

---

## Phase 5: Deploy (Task 15)

### Task 15: Docker + Render Deployment

**Step 1: Write Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Write docker-compose.yml**

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: ./backend/.env
    volumes: ["./chroma_data:/app/chroma_data"]
  frontend:
    build: ./frontend
    ports: ["5173:80"]
```

**Step 3: Deploy to Render**

- Create Render web service for backend (Docker)
- Create Render static site for frontend (Vite build)
- Set environment variables on Render dashboard

**Step 4: Verify live URL works**

**Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Docker and deployment configuration"
```

---

## Summary

| Phase | Tasks | Estimated Days | What You Get |
|-------|-------|---------------|-------------|
| 1: Foundation | 1–4 | 2-3 days | Project scaffold, all models, LLM + Tavily + VDB services |
| 2: Core Agents | 5–8 | 3-4 days | Research Scout (with AEO), Profile, Audience, Content agents |
| 3: API + Frontend | 9–11 | 3-4 days | Working end-to-end demo with wizard UI |
| 4: Sales + Ads | 12–14 | 2-3 days | Sales pipeline, ElevenLabs, ad images |
| 5: Deploy | 15 | 1 day | Live on Render with shareable URL |

**Total: ~12-15 days with Claude Code assistance**

The critical path is Phases 1-3: once you have the working end-to-end demo with Agents 0-3, you have a demoable product. Phases 4-5 are polish and wow factors.
