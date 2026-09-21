from app.services.llm_service import LLMService
from app.services.mitre_service import MitreService
from app.services.rag_service import RagService


def test_mitre_stub_disabled():
    """Verify MITRE service returns empty list when disabled."""
    service = MitreService(enabled=False)
    assert service.map_techniques({}, 0.8) == []


def test_rag_stub_disabled():
    """Verify RAG service returns empty context when disabled."""
    service = RagService(enabled=False)
    assert service.retrieve_context({}, 0.8) == []


def test_llm_stub_disabled():
    """Verify LLM service returns empty explanation when disabled."""
    service = LLMService(enabled=False)
    exp = service.explain({}, 0.8, True)
    assert exp.summary is None
    assert exp.reasoning is None
    assert exp.recommendations == []
