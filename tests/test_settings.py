from pathlib import Path

from app.settings import MODEL_TIERS, get_model


def test_model_tiers_have_three_levels():
    assert set(MODEL_TIERS) == {"cheap", "standard", "deep"}


def test_get_model_returns_configured_id():
    assert get_model("standard") == MODEL_TIERS["standard"]
    assert get_model("standard").startswith("claude-")


def test_get_model_rejects_unknown_tier():
    import pytest
    with pytest.raises(KeyError):
        get_model("nope")


def test_requirements_include_openai_backend_dependency():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "langchain-openai" in requirements
