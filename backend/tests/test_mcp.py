import pytest
from backend.app.mcp_server import (
    check_campus_service_status,
    create_sanitized_oit_ticket,
    lookup_utd_it_policy,
    run_mcp_tool_for_prompt,
)


def test_lookup_utd_it_policy():
    res = lookup_utd_it_policy("cometnet")
    assert res["status"] == "FOUND"
    assert "policy_id" in res
    assert "ISS-03" in res["policy_id"]

    ferpa = lookup_utd_it_policy("ferpa")
    assert ferpa["status"] == "FOUND"
    assert "FERPA" in ferpa["policy_id"]


def test_check_campus_service_status():
    status = check_campus_service_status("galaxy")
    assert status["status"] == "OPERATIONAL"
    assert "latency_ms" in status
    assert status["latency_ms"] > 0


def test_create_sanitized_oit_ticket_success():
    ticket = create_sanitized_oit_ticket(
        category="Network & Access",
        sanitized_summary="Student [REDACTED_UTD_ID] cannot access campus portal.",
    )
    assert ticket["status"] == "CREATED"
    assert ticket["ticket_id"].startswith("INC-UTD-")


def test_create_sanitized_oit_ticket_pii_violation_rejection():
    # Attempting to submit raw SSN must fail
    with pytest.raises(ValueError, match="FERPA Violation"):
        create_sanitized_oit_ticket(
            category="Accounts",
            sanitized_summary="Student SSN is 123-45-6789, please reset access.",
        )

    # Attempting to submit raw 10-digit UTD ID must fail
    with pytest.raises(ValueError, match="FERPA Violation"):
        create_sanitized_oit_ticket(
            category="Accounts",
            sanitized_summary="Please lookup student 2021234567.",
        )

    # Attempting to submit raw email must fail
    with pytest.raises(ValueError, match="FERPA Violation"):
        create_sanitized_oit_ticket(
            category="Accounts",
            sanitized_summary="Contact user at temoc@utdallas.edu for updates.",
        )


@pytest.mark.asyncio
async def test_run_mcp_tool_for_prompt():
    # Policy prompt
    pol_result = await run_mcp_tool_for_prompt("What is the UTD CometNet Wi-Fi security policy?")
    assert pol_result is not None
    assert pol_result["server"] == "UTD-OIT-Tools"
    assert pol_result["tool"] == "lookup_utd_it_policy"
    assert pol_result["output"] is not None

    # Status prompt
    stat_result = await run_mcp_tool_for_prompt("Is Galaxy portal down or operational right now?")
    assert stat_result is not None
    assert stat_result["tool"] == "check_campus_service_status"

    # Ticket prompt
    ticket_result = await run_mcp_tool_for_prompt("Submit a ticket for broken campus Wi-Fi access in library.")
    assert ticket_result is not None
    assert ticket_result["tool"] == "create_sanitized_oit_ticket"


@pytest.mark.asyncio
async def test_mcp_status_endpoint():
    from backend.app.main import app
    import httpx
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/mcp/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["server"] == "UTD-OIT-Tools"
        assert data["tool_count"] == 3
        tool_names = [t["name"] for t in data["tools"]]
        assert "lookup_utd_it_policy" in tool_names
        assert "check_campus_service_status" in tool_names
        assert "create_sanitized_oit_ticket" in tool_names
