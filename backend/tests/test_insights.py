from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, create_chat, signup_user

SAMPLE_SUMMARY = {
    "businessOverview": "Acme Corp operates in software.",
    "revenueAndProfit": "Revenue grew 12%.",
    "keyHighlights": ["Strong cash position"],
    "managementOutlook": "Positive outlook for next year.",
    "notableChanges": "New product launch.",
}

SAMPLE_RISKS = {
    "risks": [
        {
            "category": "Regulatory",
            "description": "Changes in data privacy laws may increase compliance costs.",
            "severity": "Medium",
        }
    ]
}


@pytest.fixture
def mock_generate_summary():
    with patch(
        "services.analysis_service.generate_executive_summary",
        new_callable=AsyncMock,
    ) as mock:
        from models.insights import ExecutiveSummaryData

        mock.return_value = ExecutiveSummaryData.model_validate(SAMPLE_SUMMARY)
        yield mock


@pytest.fixture
def mock_generate_risks():
    with patch(
        "services.analysis_service.generate_risk_analysis",
        new_callable=AsyncMock,
    ) as mock:
        from models.insights import RiskAnalysisData

        mock.return_value = RiskAnalysisData.model_validate(SAMPLE_RISKS)
        yield mock


async def _mark_chat_ready(chat_id: str):
    import core.database as database

    await database._db.chats.update_one(
        {"chatId": chat_id},
        {
            "$set": {
                "documentUploaded": True,
                "ingestionStatus": "completed",
                "vectorCollection": f"axiom_{chat_id}",
                "documentName": "annual-report.pdf",
            }
        },
    )


async def test_get_summary_idle_without_generation(client: AsyncClient):
    signup = await signup_user(client, email="idle-user@example.com")
    token = signup["token"]
    chat_id = "idle-chat"
    await create_chat(client, token, chat_id=chat_id)
    await _mark_chat_ready(chat_id)

    response = await client.get(
        f"/insights/{chat_id}/summary",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "idle"


async def test_executive_summary_generates_on_post_and_caches(
    client: AsyncClient,
    mock_generate_summary,
):
    signup = await signup_user(client, email="summary-user@example.com")
    token = signup["token"]
    chat_id = "summary-chat"
    await create_chat(client, token, chat_id=chat_id)
    await _mark_chat_ready(chat_id)

    response = await client.post(
        f"/insights/{chat_id}/summary",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["data"]["businessOverview"] == SAMPLE_SUMMARY["businessOverview"]
    assert body["cached"] is False
    mock_generate_summary.assert_called_once()

    import core.database as database

    stored = await database._db.chats.find_one({"chatId": chat_id})
    assert stored["executiveSummary"] is not None
    assert any(m.get("insightType") == "summary" for m in stored["messages"])

    get_response = await client.get(
        f"/insights/{chat_id}/summary",
        headers=auth_headers(token),
    )
    assert get_response.json()["status"] == "ready"
    assert get_response.json()["cached"] is True
    assert mock_generate_summary.call_count == 1


async def test_risk_analysis_generates_on_post(
    client: AsyncClient,
    mock_generate_risks,
):
    signup = await signup_user(client, email="risk-user@example.com")
    token = signup["token"]
    chat_id = "risk-chat"
    await create_chat(client, token, chat_id=chat_id)
    await _mark_chat_ready(chat_id)

    response = await client.post(
        f"/insights/{chat_id}/risks",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert len(body["data"]["risks"]) == 1

    import core.database as database

    stored = await database._db.chats.find_one({"chatId": chat_id})
    assert stored["riskAnalysis"] is not None
    assert any(m.get("insightType") == "risks" for m in stored["messages"])


async def test_insights_unavailable_before_ingestion(client: AsyncClient):
    signup = await signup_user(client, email="pending-user@example.com")
    token = signup["token"]
    chat_id = "pending-chat"
    await create_chat(client, token, chat_id=chat_id)

    response = await client.get(
        f"/insights/{chat_id}/summary",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
