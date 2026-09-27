"""
Dristik AI Configuration
Loads settings from environment variables with validation.
"""
from pathlib import Path
from typing import Any, Optional, List, Dict
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Ensure backend/.env variables are populated into os.environ for os.environ.get calls
_backend_root = Path(__file__).resolve().parent.parent.parent
for _candidate in (_backend_root / ".env", Path(".env").resolve(), Path("backend/.env").resolve()):
    if _candidate.is_file():
        load_dotenv(dotenv_path=_candidate, override=False)
        break

# Live Anthropic IDs (Claude 3 Haiku / 3.5 Sonnet were retired in 2026).
ANTHROPIC_DEFAULT_FAST = "claude-haiku-4-5-20251001"
ANTHROPIC_DEFAULT_REASONING = "claude-haiku-4-5-20251001"
ANTHROPIC_FALLBACK_MODEL = "claude-sonnet-4-6"
# Groq shut down llama-3.1-8b-instant and llama-3.3-70b-versatile for free/dev
# tiers on 2026-08-16. Live replacements are openai/gpt-oss-* and qwen/qwen3.6-27b.
GROQ_DEFAULT_FAST = "openai/gpt-oss-20b"
GROQ_DEFAULT_REASONING = "openai/gpt-oss-120b"
_GROQ_LIVE_PREFIXES = ("openai/gpt-oss-", "qwen/qwen")
_GROQ_RETIRED_MODELS = {
    "llama-3.1-8b-instant": GROQ_DEFAULT_FAST,
    "llama-3.3-70b-versatile": GROQ_DEFAULT_REASONING,
    "llama3-8b-8192": GROQ_DEFAULT_FAST,
    "llama3-70b-8192": GROQ_DEFAULT_REASONING,
    "gemma2-9b-it": GROQ_DEFAULT_FAST,
    "mixtral-8x7b-32768": GROQ_DEFAULT_REASONING,
    "qwen/qwen3-32b": GROQ_DEFAULT_REASONING,
    "qwen-qwq-32b": GROQ_DEFAULT_REASONING,
    "meta-llama/llama-4-scout-17b-16e-instruct": GROQ_DEFAULT_REASONING,
    "meta-llama/llama-4-maverick-17b-128e-instruct": GROQ_DEFAULT_REASONING,
}
_ANTHROPIC_RETIRED_MODELS = {
    "claude-3-haiku-20240307": ANTHROPIC_DEFAULT_FAST,
    "claude-3-haiku": ANTHROPIC_DEFAULT_FAST,
    "claude-3-5-haiku-20241022": ANTHROPIC_DEFAULT_FAST,
    "claude-3-5-haiku-latest": ANTHROPIC_DEFAULT_FAST,
    "claude-3-5-haiku": ANTHROPIC_DEFAULT_FAST,
    "claude-3-5-sonnet-20241022": ANTHROPIC_DEFAULT_REASONING,
    "claude-3-5-sonnet-20240620": ANTHROPIC_DEFAULT_REASONING,
    "claude-3-5-sonnet-latest": ANTHROPIC_DEFAULT_REASONING,
    "claude-3-5-sonnet": ANTHROPIC_DEFAULT_REASONING,
    "claude-3-7-sonnet-20250219": ANTHROPIC_DEFAULT_REASONING,
    "claude-3-7-sonnet-latest": ANTHROPIC_DEFAULT_REASONING,
    "claude-3-sonnet-20240229": ANTHROPIC_DEFAULT_REASONING,
    "claude-sonnet-4-20250514": ANTHROPIC_DEFAULT_REASONING,
    "claude-3-opus-20240229": "claude-opus-4-6",
    "claude-opus-4-20250514": "claude-opus-4-6",
}


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Dristik AI"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Multi-Provider LLM Gateway Configuration
    # Supported providers: "auto" | "gemini" | "groq" | "openrouter" | "together"
    LLM_PROVIDER: str = Field(default="auto", description="Active LLM Provider: auto | anthropic | gemini | groq | openrouter | together")
    
    # Provider-Specific API Keys
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API Key (Claude)")
    CLAUDE_API_KEY: Optional[str] = Field(default=None, description="Alternative alias for Anthropic API Key")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key (AI Studio)")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Alternative alias for Gemini API Key")
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API Key (Free tier available)")
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, description="OpenRouter API Key (Multi-model aggregator)")
    TOGETHER_API_KEY: Optional[str] = Field(default=None, description="Together AI API Key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API Key")
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, description="DeepSeek API Key")
    PERPLEXITY_API_KEY: Optional[str] = Field(default=None, description="Perplexity API Key")
    XAI_API_KEY: Optional[str] = Field(default=None, description="xAI Grok API Key")
    MOONSHOT_API_KEY: Optional[str] = Field(default=None, description="Moonshot Kimi API Key")
    
    # Generic Overrides (Optional)
    LLM_API_KEY: Optional[str] = Field(default=None, description="Generic LLM API Key override")
    LLM_BASE_URL: Optional[str] = Field(default=None, description="Generic LLM Base URL override")
    
    # Model Configuration (Set LLM_MODEL to apply one model to all tasks, or set FAST/REASONING individually)
    LLM_MODEL: Optional[str] = Field(default=None, description="Global model override for all tasks (e.g. llama-3.1-8b-instant, gemini-2.0-flash)")
    LLM_MODEL_FAST: Optional[str] = None
    LLM_MODEL_REASONING: Optional[str] = None
    LLM_MODEL_CRITIC: Optional[str] = None
    LLM_MODEL_SYNTHESIS: Optional[str] = None

    # Provider specific model overrides
    ANTHROPIC_MODEL: Optional[str] = None
    ANTHROPIC_MODEL_FAST: Optional[str] = None
    ANTHROPIC_MODEL_REASONING: Optional[str] = None
    GROQ_MODEL: Optional[str] = None
    GROQ_MODEL_FAST: Optional[str] = None
    GROQ_MODEL_REASONING: Optional[str] = None
    GEMINI_MODEL: Optional[str] = None
    OPENROUTER_MODEL: Optional[str] = None
    OPENROUTER_MODEL_FAST: Optional[str] = None
    OPENROUTER_MODEL_REASONING: Optional[str] = None
    OPENROUTER_SITE_URL: Optional[str] = Field(default="https://dristik.ai", description="HTTP-Referer header for OpenRouter rankings")
    OPENROUTER_SITE_NAME: Optional[str] = Field(default="Dristik AI", description="X-Title header for OpenRouter rankings")
    TOGETHER_MODEL: Optional[str] = None

    # AI Citation Tracker Engine Configuration
    AI_CITATION_CROSS_PROVIDER: bool = Field(default=False, description="Enable multi-engine citation tracker fan-out across providers")
    AI_CITATION_CLAUDE_ACTIVE: Optional[bool] = None
    AI_CITATION_CLAUDE_PROVIDER: Optional[str] = None
    AI_CITATION_CLAUDE_API_KEY: Optional[str] = None
    AI_CITATION_CLAUDE_MODEL: Optional[str] = None

    AI_CITATION_LLAMA_ACTIVE: Optional[bool] = None
    AI_CITATION_LLAMA_PROVIDER: Optional[str] = None
    AI_CITATION_LLAMA_API_KEY: Optional[str] = None
    AI_CITATION_LLAMA_MODEL: Optional[str] = None

    AI_CITATION_GEMINI_ACTIVE: Optional[bool] = None
    AI_CITATION_GEMINI_PROVIDER: Optional[str] = None
    AI_CITATION_GEMINI_API_KEY: Optional[str] = None
    AI_CITATION_GEMINI_MODEL: Optional[str] = None

    AI_CITATION_CHATGPT_ACTIVE: Optional[bool] = None
    AI_CITATION_CHATGPT_PROVIDER: Optional[str] = None
    AI_CITATION_CHATGPT_API_KEY: Optional[str] = None
    AI_CITATION_CHATGPT_MODEL: Optional[str] = None

    AI_CITATION_PERPLEXITY_ACTIVE: Optional[bool] = None
    AI_CITATION_PERPLEXITY_PROVIDER: Optional[str] = None
    AI_CITATION_PERPLEXITY_API_KEY: Optional[str] = None
    AI_CITATION_PERPLEXITY_MODEL: Optional[str] = None

    AI_CITATION_DEEPSEEK_ACTIVE: Optional[bool] = None
    AI_CITATION_DEEPSEEK_PROVIDER: Optional[str] = None
    AI_CITATION_DEEPSEEK_API_KEY: Optional[str] = None
    AI_CITATION_DEEPSEEK_MODEL: Optional[str] = None

    AI_CITATION_GROK_ACTIVE: Optional[bool] = None
    AI_CITATION_GROK_PROVIDER: Optional[str] = None
    AI_CITATION_GROK_API_KEY: Optional[str] = None
    AI_CITATION_GROK_MODEL: Optional[str] = None

    AI_CITATION_KIMI_ACTIVE: Optional[bool] = None
    AI_CITATION_KIMI_PROVIDER: Optional[str] = None
    AI_CITATION_KIMI_API_KEY: Optional[str] = None
    AI_CITATION_KIMI_MODEL: Optional[str] = None

    # Legacy Together AI fields for backwards compatibility
    TOGETHER_BASE_URL: str = "https://api.together.xyz/v1"
    TOGETHER_MODEL_FAST: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    TOGETHER_MODEL_REASONING: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    TOGETHER_MODEL_CRITIC: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    TOGETHER_MODEL_SYNTHESIS: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    
    # Inference Parameters
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 3000
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3
    LLM_MAX_CONCURRENCY: int = Field(default=2, description="Max concurrent in-flight requests per LLM provider to eliminate 429 thundering herd")
    ANTHROPIC_RPM: int = Field(default=15, description="Requests per minute limit for Anthropic Messages API")
    ANTHROPIC_TPM: int = Field(default=40000, description="Tokens per minute limit for Anthropic Messages API")
    ENABLE_CROSS_PROVIDER_CASCADE: bool = Field(default=True, description="Cascade to secondary provider if primary provider is exhausted")
    # Actual USD per 1M tokens you pay. Both must be set. They override the
    # published list price for every call the provider did not bill in-band.
    LLM_COST_INPUT_PER_MILLION: Optional[float] = None
    LLM_COST_OUTPUT_PER_MILLION: Optional[float] = None
    # JSON rates for specific models. A provider bill still wins.
    # {"groq/openai/gpt-oss-20b": {"input": 0.075, "output": 0.30}}
    LLM_MODEL_PRICES: Optional[str] = None
    
    # Legacy aliases
    TOGETHER_TEMPERATURE: float = 0.2
    TOGETHER_MAX_TOKENS: int = 3000
    TOGETHER_TIMEOUT_SECONDS: int = 60
    TOGETHER_MAX_RETRIES: int = 3
    
    # Embedding Configuration (HuggingFace local E5-Small & OpenRouter remote)
    EMBEDDING_PROVIDER: str = Field(default="huggingface", description="Embedding provider: huggingface (local) | openrouter")
    EMBEDDING_MODEL: str = Field(default="intfloat/e5-small-v2", description="Embedding model identifier (~130MB, 384-dim)")
    EMBEDDING_API_KEY: Optional[str] = Field(default=None, description="API key if using openrouter embedding provider")
    EMBEDDING_BASE_URL: str = Field(default="https://openrouter.ai/api/v1", description="API base URL for remote embeddings")
    EMBEDDING_DEVICE: str = Field(default="cpu", description="Embedding device for local huggingface: cpu | mps | cuda | auto")
    EMBEDDING_BATCH_SIZE: int = Field(default=32, description="Batch size for generating embeddings")
    HF_TOKEN: Optional[str] = Field(default=None, description="Hugging Face API token for authenticated Hub access and higher rate limits")
    HUGGINGFACE_TOKEN: Optional[str] = Field(default=None, description="Hugging Face API token alias")

    # Crawling & Ingestion
    FIRECRAWL_API_KEY: Optional[str] = None
    MAX_CRAWL_PAGES: Any = Field(default=10, description="Page limit: 10 | 25 | 50 | 200 | 500 | 'quick' | 'standard' | 'deep' | 'enterprise'")
    CRAWL_TIERS: Dict[str, int] = Field(
        default_factory=lambda: {
            "quick": 10,
            "standard": 50,
            "deep": 500,
            "enterprise": 500,
        }
    )
    CRAWL_TIMEOUT_SECONDS: int = 15
    CRAWL_CONCURRENCY: int = 3
    JS_RENDER_THIN_PAGES: bool = True
    FIRECRAWL_WAIT_MS: int = 3000
    PLAYWRIGHT_ENABLED: bool = True
    PLAYWRIGHT_TIMEOUT_MS: int = 15000
    PLAYWRIGHT_HEADLESS: bool = True
    USER_AGENT: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    def get_max_crawl_pages(self, override: Optional[Any] = None) -> int:
        """
        Resolves maximum crawl pages allowing integer counts or named tiers:
        'quick' -> 10, 'standard' -> 50, 'deep' / 'enterprise' / 'all' -> 500.
        Invalid strings fallback to default 5.
        """
        raw = override if override is not None else self.MAX_CRAWL_PAGES
        if isinstance(raw, str):
            s = raw.strip().lower()
            if s in self.CRAWL_TIERS:
                return self.CRAWL_TIERS[s]
            if s in ("all", "-1", "deep", "full", "max", "enterprise"):
                return 500
            try:
                return int(s)
            except ValueError:
                return 5
        try:
            val = int(raw)
            return 500 if val <= 0 else val
        except (ValueError, TypeError):
            return 5
    
    # Security
    SSRF_PROTECTION_ENABLED: bool = True
    ALLOWED_SCHEMES: List[str] = ["http", "https"]
    AUTH_SECRET: str = Field(default="dristik-dev-secret-change-me", description="Secret used to bind session tokens")
    AUTH_DATABASE_PATH: str = Field(default="data/dristik.db")
    SESSION_DAYS: int = 14
    FRONTEND_URL: str = "http://localhost:5173"
    SYSTEM_ADMIN_EMAIL: str = "admin@dristik.ai"
    SYSTEM_ADMIN_PASSWORD: str = "DristikAdmin1!"
    SYSTEM_ADMIN_NAME: str = "Dristik Admin"
    
    # Budget & Cost Limits
    ANALYSIS_MAX_COST_USD: float = 0.05
    ANALYSIS_MAX_MODEL_CALLS: int = 25
    ANALYSIS_MAX_REASONING_CALLS: int = 6
    ANALYSIS_TIMEOUT_SECONDS: int = 180
    
    # Razorpay Payment Gateway Configuration
    RAZORPAY_KEY_ID: Optional[str] = Field(default=None, description="Razorpay Key ID (e.g. rzp_test_xxx or rzp_live_xxx)")
    RAZORPAY_KEY_SECRET: Optional[str] = Field(default=None, description="Razorpay Key Secret")
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Razorpay Webhook Secret")
    RAZORPAY_CURRENCY: str = "INR"

    # External ground truth. Absent keys stay NOT_CONFIGURED. Never invent the metric.
    CRUX_API_KEY: Optional[str] = Field(default=None, description="Chrome UX Report API key. Not a substitute for lab TTFB.")
    DATAFORSEO_LOGIN: Optional[str] = None
    DATAFORSEO_PASSWORD: Optional[str] = None
    CLEARBIT_API_KEY: Optional[str] = None
    BUILTWITH_API_KEY: Optional[str] = None
    CRUNCHBASE_API_KEY: Optional[str] = None
    G2_API_KEY: Optional[str] = None
    LINKEDIN_API_KEY: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = None
    OAUTH_REDIRECT_URI: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    # Optional dedicated SSO client ID/secrets (falls back to GOOGLE_CLIENT_ID / GITHUB_CLIENT_ID if unset)
    GOOGLE_SSO_CLIENT_ID: Optional[str] = None
    GOOGLE_SSO_CLIENT_SECRET: Optional[str] = None
    GITHUB_SSO_CLIENT_ID: Optional[str] = None
    GITHUB_SSO_CLIENT_SECRET: Optional[str] = None
    SHOPIFY_CLIENT_ID: Optional[str] = None
    SHOPIFY_CLIENT_SECRET: Optional[str] = None
    WEBFLOW_CLIENT_ID: Optional[str] = None
    WEBFLOW_CLIENT_SECRET: Optional[str] = None
    HUBSPOT_CLIENT_ID: Optional[str] = None
    HUBSPOT_CLIENT_SECRET: Optional[str] = None
    SALESFORCE_CLIENT_ID: Optional[str] = None
    SALESFORCE_CLIENT_SECRET: Optional[str] = None
    STRIPE_CLIENT_ID: Optional[str] = None
    STRIPE_CLIENT_SECRET: Optional[str] = None
    WORDPRESS_CLIENT_ID: Optional[str] = None
    WORDPRESS_CLIENT_SECRET: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GA4_PROPERTY_ID: Optional[str] = None

    def get_google_sso_client(self) -> tuple[Optional[str], Optional[str]]:
        cid = self.GOOGLE_SSO_CLIENT_ID or self.GOOGLE_CLIENT_ID
        sec = self.GOOGLE_SSO_CLIENT_SECRET or self.GOOGLE_CLIENT_SECRET
        return cid, sec

    def get_github_sso_client(self) -> tuple[Optional[str], Optional[str]]:
        cid = self.GITHUB_SSO_CLIENT_ID or self.GITHUB_CLIENT_ID
        sec = self.GITHUB_SSO_CLIENT_SECRET or self.GITHUB_CLIENT_SECRET
        return cid, sec

    # Notifications. Missing SMTP reports delivery_status=not_configured.
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    NOTIFY_EMAIL: Optional[str] = None

    # Data Integrity & Production Safety Guardrails
    PRODUCTION_DATA_INTEGRITY_MODE: bool = Field(
        default=True,
        description="Zero-Fake integrity mode: blocks mock payments, fake signatures, and ungrounded fallbacks"
    )
    ALLOW_PAYMENT_TEST_MOCKS: bool = Field(
        default=False,
        description="Strictly for isolated automated tests in non-production environments"
    )
    
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @staticmethod
    def _coerce_groq_model(name: Optional[str], fallback: str) -> str:
        """Map retired Groq IDs to live ones. Keep Groq-hosted openai/ and qwen/ ids."""
        n = (name or "").strip()
        if not n:
            return fallback
        lowered = n.lower()
        if lowered in _GROQ_RETIRED_MODELS:
            return _GROQ_RETIRED_MODELS[lowered]
        if lowered.startswith(_GROQ_LIVE_PREFIXES):
            return n
        if "/" in n or lowered.endswith(":free"):
            return fallback
        return n

    @staticmethod
    def _coerce_anthropic_model(name: Optional[str], fallback: str) -> str:
        """Map retired Claude IDs and reject OpenRouter-style ids for the native Anthropic API."""
        n = (name or "").strip()
        if not n:
            return fallback
        lowered = n.lower()
        if "/" in n or lowered.endswith(":free"):
            return fallback
        return _ANTHROPIC_RETIRED_MODELS.get(lowered, n)

    def get_configured_providers(self) -> List[str]:
        """Returns list of providers with available API keys."""
        configured = []
        if self.ANTHROPIC_API_KEY or self.CLAUDE_API_KEY:
            configured.append("anthropic")
        if self.GEMINI_API_KEY or self.GOOGLE_API_KEY:
            configured.append("gemini")
        if self.GROQ_API_KEY:
            configured.append("groq")
        if self.OPENROUTER_API_KEY:
            configured.append("openrouter")
        if self.TOGETHER_API_KEY:
            configured.append("together")
        if self.LLM_API_KEY:
            configured.append("custom")
        return configured

    def get_active_provider(self) -> str:
        """Determines active provider based on LLM_PROVIDER setting or available keys."""
        prov = (self.LLM_PROVIDER or "auto").lower().strip()
        if prov != "auto" and prov != "":
            return prov
            
        # Auto-selection priority: anthropic -> gemini -> groq -> openrouter -> together -> custom
        if self.ANTHROPIC_API_KEY or self.CLAUDE_API_KEY:
            return "anthropic"
        if self.GEMINI_API_KEY or self.GOOGLE_API_KEY:
            return "gemini"
        if self.GROQ_API_KEY:
            return "groq"
        if self.OPENROUTER_API_KEY:
            return "openrouter"
        if self.TOGETHER_API_KEY:
            return "together"
        if self.LLM_API_KEY:
            return "custom"
        return "none"

    def get_llm_credentials(self) -> dict:
        """
        Resolves (api_key, base_url, model_fast, model_reasoning, provider_name).
        """
        provider = self.get_active_provider()
        
        # 0. Anthropic Claude
        if provider in ["anthropic", "claude"]:
            api_key = self.ANTHROPIC_API_KEY or self.CLAUDE_API_KEY or self.LLM_API_KEY
            base_url = self.LLM_BASE_URL or "https://api.anthropic.com/v1"
            # Provider-specific Anthropic models always win over the global LLM_MODEL
            # override (which may be an OpenRouter id like org/model:free).
            fast_model = self._coerce_anthropic_model(
                self.ANTHROPIC_MODEL_FAST or self.ANTHROPIC_MODEL or self.LLM_MODEL_FAST or self.LLM_MODEL,
                ANTHROPIC_DEFAULT_FAST,
            )
            reasoning_model = self._coerce_anthropic_model(
                self.ANTHROPIC_MODEL_REASONING or self.ANTHROPIC_MODEL or self.LLM_MODEL_REASONING or self.LLM_MODEL,
                ANTHROPIC_DEFAULT_REASONING,
            )
            return {
                "provider": "anthropic",
                "display_name": "Anthropic Claude",
                "api_key": api_key,
                "base_url": base_url,
                "model_fast": fast_model,
                "model_reasoning": reasoning_model,
                "extra_headers": {
                    "anthropic-version": "2023-06-01",
                    "x-api-key": api_key or ""
                }
            }
            
        # 1. Google Gemini
        elif provider in ["gemini", "google"]:
            api_key = self.GEMINI_API_KEY or self.GOOGLE_API_KEY or self.LLM_API_KEY
            base_url = self.LLM_BASE_URL or "https://generativelanguage.googleapis.com/v1beta/openai"
            model_override = self.LLM_MODEL or self.GEMINI_MODEL
            fast_model = self.LLM_MODEL_FAST or model_override or "gemini-2.0-flash"
            reasoning_model = self.LLM_MODEL_REASONING or model_override or "gemini-2.0-flash"
            return {
                "provider": "gemini",
                "display_name": "Google Gemini",
                "api_key": api_key,
                "base_url": base_url,
                "model_fast": fast_model,
                "model_reasoning": reasoning_model,
                "extra_headers": {}
            }
            
        # 2. Groq
        elif provider == "groq":
            api_key = self.GROQ_API_KEY or self.LLM_API_KEY
            base_url = self.LLM_BASE_URL or "https://api.groq.com/openai/v1"
            model_override = self.LLM_MODEL or self.GROQ_MODEL
            fast_model = self._coerce_groq_model(
                self.GROQ_MODEL_FAST or self.LLM_MODEL_FAST or model_override,
                GROQ_DEFAULT_FAST,
            )
            reasoning_model = self._coerce_groq_model(
                self.GROQ_MODEL_REASONING or self.LLM_MODEL_REASONING or model_override,
                GROQ_DEFAULT_REASONING,
            )
            return {
                "provider": "groq",
                "display_name": "Groq LPU",
                "api_key": api_key,
                "base_url": base_url,
                "model_fast": fast_model,
                "model_reasoning": reasoning_model,
                "extra_headers": {}
            }
            
        # 3. OpenRouter
        elif provider == "openrouter":
            api_key = self.OPENROUTER_API_KEY or self.LLM_API_KEY
            base_url = self.LLM_BASE_URL or "https://openrouter.ai/api/v1"
            model_override = self.LLM_MODEL or self.OPENROUTER_MODEL
            fast_model = self.OPENROUTER_MODEL_FAST or self.LLM_MODEL_FAST or model_override or "openai/gpt-4o"
            reasoning_model = self.OPENROUTER_MODEL_REASONING or self.LLM_MODEL_REASONING or model_override or "openai/gpt-4o"
            site_url = self.OPENROUTER_SITE_URL or "https://dristik.ai"
            site_name = self.OPENROUTER_SITE_NAME or "Dristik AI"
            return {
                "provider": "openrouter",
                "display_name": "OpenRouter",
                "api_key": api_key,
                "base_url": base_url,
                "model_fast": fast_model,
                "model_reasoning": reasoning_model,
                "extra_headers": {
                    "HTTP-Referer": site_url,
                    "X-Title": site_name
                }
            }
            
        # 4. Together AI (or fallback default)
        else:
            api_key = self.TOGETHER_API_KEY or self.LLM_API_KEY
            base_url = self.LLM_BASE_URL or self.TOGETHER_BASE_URL or "https://api.together.xyz/v1"
            model_override = self.LLM_MODEL or self.TOGETHER_MODEL
            fast_model = self.LLM_MODEL_FAST or self.TOGETHER_MODEL_FAST or model_override or "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
            reasoning_model = self.LLM_MODEL_REASONING or self.TOGETHER_MODEL_REASONING or model_override or "meta-llama/Llama-3.3-70B-Instruct-Turbo"
            return {
                "provider": "together",
                "display_name": "Together AI",
                "api_key": api_key,
                "base_url": base_url,
                "model_fast": fast_model,
                "model_reasoning": reasoning_model,
                "extra_headers": {}
            }

    @property
    def has_active_llm_key(self) -> bool:
        creds = self.get_llm_credentials()
        return bool(creds.get("api_key") and creds["api_key"].strip())


def validate_production_configuration(settings_obj: Settings) -> None:
    """
    Production Startup Safety Check.
    Fails startup immediately if dangerous default secrets or mock configurations are active in production.
    """
    is_prod = settings_obj.ENVIRONMENT.lower() in ("production", "prod")

    if is_prod:
        if settings_obj.DEBUG:
            raise RuntimeError(
                "CRITICAL CONFIGURATION ERROR: DEBUG=True is forbidden in production. Set DEBUG=false."
            )
        if settings_obj.AUTH_SECRET == "dristik-dev-secret-change-me" or len(settings_obj.AUTH_SECRET) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Default or weak AUTH_SECRET detected in production. Set a cryptographically random secret of at least 32 characters."
            )
        if settings_obj.SYSTEM_ADMIN_PASSWORD == "DristikAdmin1!":
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Default SYSTEM_ADMIN_PASSWORD detected in production. Set a secure password."
            )
        if settings_obj.ALLOW_PAYMENT_TEST_MOCKS:
            raise RuntimeError(
                "CRITICAL DATA INTEGRITY ERROR: ALLOW_PAYMENT_TEST_MOCKS cannot be enabled in production."
            )
        if not settings_obj.PRODUCTION_DATA_INTEGRITY_MODE:
            raise RuntimeError(
                "CRITICAL DATA INTEGRITY ERROR: PRODUCTION_DATA_INTEGRITY_MODE must be True in production."
            )


settings = Settings()
