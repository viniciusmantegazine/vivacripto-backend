"""
Testes para os schemas Pydantic de airdrop.
"""
import pytest
from pydantic import ValidationError

from app.schemas.airdrop import AirdropPostRequest, AirdropPostResponse


def test_request_accepts_valid_data():
    req = AirdropPostRequest(
        project_name="LayerZero",
        official_url="https://layerzero.network",
        referral_url="https://app.layerzero.foundation/ref/abc",
        publish=False,
    )
    assert req.project_name == "LayerZero"
    assert str(req.official_url).startswith("https://layerzero.network")


def test_request_publish_defaults_to_false():
    req = AirdropPostRequest(
        project_name="Twitter",
        official_url="https://x.com",
        referral_url="https://x.com/ref/1",
    )
    # `publish` é opcional e default deve ser False
    assert req.publish is False


def test_request_rejects_empty_project_name():
    with pytest.raises(ValidationError):
        AirdropPostRequest(
            project_name="",
            official_url="https://x.com",
            referral_url="https://x.com/ref/1",
        )


def test_request_rejects_invalid_url():
    with pytest.raises(ValidationError):
        AirdropPostRequest(
            project_name="X",
            official_url="not-a-url",
            referral_url="https://x.com/ref/1",
        )


def test_response_serializes_with_all_fields():
    resp = AirdropPostResponse(
        success=True,
        post_id="abc-123",
        title="Title",
        slug="title",
        excerpt="Excerpt",
        image_url="https://img/x.jpg",
        word_count=600,
        sources_used=["https://x.com"],
        preview_content="# x",
    )
    payload = resp.model_dump()
    assert payload["success"] is True
    assert payload["post_id"] == "abc-123"
    assert payload["sources_used"] == ["https://x.com"]


def test_response_optional_fields_default():
    resp = AirdropPostResponse(success=False, title="", slug="", excerpt="")
    assert resp.post_id is None
    assert resp.image_url is None
    assert resp.word_count == 0
    assert resp.sources_used == []
    assert resp.preview_content is None
