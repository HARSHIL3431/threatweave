from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""
    
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    API_VERSION: str = "v1"
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # ML Model & Preprocessing Paths
    MODEL_PATH: str = "../data/processed/experiments/with_port/model.pkl"
    PREPROCESSING_CONFIG_PATH: str = "../data/processed/experiments/with_port/preprocessing_config.json"
    
    # Operating Point policy: "OP-A" (contamination offset) or "OP-B" (validation-optimal threshold)
    ACTIVE_OPERATING_POINT: str = "OP-A"
    
    # Feature toggles for future services (Phase 3+)
    MITRE_ENABLED: bool = False
    RAG_ENABLED: bool = False
    LLM_ENABLED: bool = False

    # MITRE ATT&CK knowledge base + RAG settings
    MITRE_DATA_DIR: str = "../data/mitre"
    RAG_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5
    # RAG index source URL (official MITRE CTI enterprise STIX bundle)
    MITRE_ENTERPRISE_STIX_URL: str = (
        "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    )

    # LLM explanation-layer settings.
    # The backend ONLY calls the LLM via the dedicated /explain endpoint. The
    # ML + severity + RAG detection pipeline is fully autonomous and never
    # depends on an LLM being reachable. Safe defaults keep everything working
    # when the feature is off or no API key is configured.
    LLM_PROVIDER: str = "openai"       # "openai" (OpenAI-compatible) or "mock" (offline, deterministic)
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""              # never hard-code; inject via environment or .env
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT: float = 60.0          # seconds per LLM call
    LLM_OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Report / PDF generation
    # Controlled output directory for generated reports (server-side only).
    # Path traversal is impossible: report filenames are server-generated
    # UUIDs, never derived from user input.
    REPORTS_DIR: str = "../data/reports"

    def llm_provider_slug(self) -> str:
        return self.LLM_PROVIDER.strip().lower()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("ACTIVE_OPERATING_POINT")
    @classmethod
    def validate_operating_point(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in ("OP-A", "OP-B"):
            raise ValueError(f"Invalid ACTIVE_OPERATING_POINT: {v}. Must be 'OP-A' or 'OP-B'.")
        return upper

    def resolve_path(self, path_str: str) -> Path:
        """Resolve a path whether running from backend/, repo root, or tests."""
        p = Path(path_str)
        if p.is_absolute() and p.exists():
            return p
        
        # Try direct relative to current working directory
        if p.exists():
            return p.resolve()
            
        # Try relative to repo root. Artifact paths are authored like
        # "../data/..." meaning "<repo_root>/data/...", so a leading "../"
        # must be stripped before joining onto the repo root.
        backend_dir = Path(__file__).resolve().parent.parent.parent
        repo_root = backend_dir.parent

        cleaned_path = path_str.replace("\\", "/").lstrip("./").lstrip("../")
        candidate_cleaned = (repo_root / cleaned_path).resolve()
        if candidate_cleaned.exists():
            return candidate_cleaned

        candidate_repo = (repo_root / path_str).resolve()
        if candidate_repo.exists():
            return candidate_repo
            
        candidate_backend = (backend_dir / path_str).resolve()
        if candidate_backend.exists():
            return candidate_backend

        return p.resolve()

    @property
    def resolved_model_path(self) -> Path:
        return self.resolve_path(self.MODEL_PATH)

    @property
    def resolved_preprocessing_config_path(self) -> Path:
        return self.resolve_path(self.PREPROCESSING_CONFIG_PATH)

    @property
    def resolved_mitre_data_dir(self) -> Path:
        p = self.resolve_path(self.MITRE_DATA_DIR)
        return p

    @property
    def mitre_raw_dir(self) -> Path:
        return self.resolved_mitre_data_dir / "raw"

    @property
    def mitre_processed_dir(self) -> Path:
        return self.resolved_mitre_data_dir / "processed"

    @property
    def mitre_vectorstore_dir(self) -> Path:
        return self.resolved_mitre_data_dir / "vectorstore"

    @property
    def mitre_stix_file(self) -> Path:
        return self.mitre_raw_dir / "enterprise-attack.json"

    @property
    def mitre_techniques_file(self) -> Path:
        return self.mitre_processed_dir / "techniques.json"

    @property
    def mitre_index_file(self) -> Path:
        return self.mitre_vectorstore_dir / "index.faiss"

    @property
    def mitre_index_metadata_file(self) -> Path:
        return self.mitre_vectorstore_dir / "metadata.json"

    @property
    def reports_dir(self) -> Path:
        return self.resolve_path(self.REPORTS_DIR)


settings = Settings()
