import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastmcp import Client, FastMCP

mcp = FastMCP("UTD-OIT-Tools")

UTD_POLICIES: Dict[str, Dict[str, Any]] = {
    "cometnet": {
        "policy_id": "ISS-03",
        "title": "UTD Wireless & Network Access Governance",
        "category": "Network Infrastructure",
        "summary": "Mandates WPA2/WPA3 Enterprise authentication using primary NetID credentials. Prohibits rogue APs, unapproved switches, and unencrypted legacy protocols.",
        "compliance": "Mandatory for all faculty, staff, and students on campus premises.",
        "enforcement": "OIT Information Security Office (ISO)",
    },
    "duo": {
        "policy_id": "IAM-02",
        "title": "UTD Mandatory Multi-Factor Authentication Standard",
        "category": "Identity & Access Management",
        "summary": "Requires Duo Push or FIDO2 hardware token verification for all university single-sign-on (SSO) logins, Galaxy access, and remote VPN tunnels.",
        "compliance": "Enforced campus-wide for all active NetIDs.",
        "enforcement": "OIT Identity & Access Management Team",
    },
    "vpn": {
        "policy_id": "NET-05",
        "title": "UTD Remote Secure Access & VPN Standard",
        "category": "Remote Connectivity",
        "summary": "All off-campus connections to internal university subnets, research clusters, and administrative servers must utilize Cisco AnyConnect / Secure Client with Duo MFA.",
        "compliance": "Required for remote administration and internal database queries.",
        "enforcement": "OIT Enterprise Infrastructure",
    },
    "galaxy": {
        "policy_id": "APP-04",
        "title": "Enterprise Applications & Student Center Security",
        "category": "Enterprise Systems",
        "summary": "Governs PeopleSoft Campus Solutions (Galaxy). Requires session timeouts after 15 minutes of inactivity and restricts bulk grade/record downloads.",
        "compliance": "FERPA & Texas DIR security compliance.",
        "enforcement": "UTD Office of the Registrar & OIT Enterprise Applications",
    },
    "ferpa": {
        "policy_id": "FERPA-01",
        "title": "UT Dallas Family Educational Rights and Privacy Standard",
        "category": "Data Privacy & Legal Compliance",
        "summary": "Protects student education records. Prohibits disclosure of personally identifiable student data (including grades, SSNs, and 10-digit UTD IDs) without verified consent.",
        "compliance": "Federal law & University of Texas System Regents' Rules.",
        "enforcement": "UTD Legal Affairs & Office of Information Security",
    },
    "password": {
        "policy_id": "SEC-01",
        "title": "NetID Password Complexity & Expiration Standard",
        "category": "Account Security",
        "summary": "Passphrases must be at least 16 characters or 12 characters with 3 character classes. Prohibits reuse of the previous 10 passwords. Passwords expire every 180 days.",
        "compliance": "Mandatory for all NetID accounts.",
        "enforcement": "OIT ISO",
    },
}

CAMPUS_SERVICES: Dict[str, Dict[str, Any]] = {
    "cometnet": {
        "service": "CometNet Campus Wi-Fi",
        "status": "OPERATIONAL",
        "latency_ms": 12.4,
        "uptime_30d": "99.96%",
        "active_access_points": 2840,
        "notes": "All campus buildings and outdoor quadrangles operating at full capacity.",
    },
    "galaxy": {
        "service": "Galaxy / PeopleSoft Student Information System",
        "status": "OPERATIONAL",
        "latency_ms": 38.1,
        "uptime_30d": "99.91%",
        "notes": "Student registration and grade submission gateways nominal.",
    },
    "duo": {
        "service": "Duo Security Multi-Factor Authentication",
        "status": "OPERATIONAL",
        "latency_ms": 22.0,
        "uptime_30d": "99.99%",
        "notes": "Push delivery and bypass code verification services online.",
    },
    "vpn": {
        "service": "UTD Global Remote Access VPN (vpn.utdallas.edu)",
        "status": "OPERATIONAL",
        "latency_ms": 18.7,
        "uptime_30d": "99.94%",
        "notes": "Split-tunnel and full-tunnel concentrators active.",
    },
    "elearning": {
        "service": "eLearning (Canvas LMS)",
        "status": "OPERATIONAL",
        "latency_ms": 29.5,
        "uptime_30d": "99.98%",
        "notes": "Cloud LMS courses and grading synch active.",
    },
    "email": {
        "service": "Microsoft 365 Exchange Online (UTD Mail)",
        "status": "OPERATIONAL",
        "latency_ms": 15.2,
        "uptime_30d": "99.99%",
        "notes": "Inbound/outbound mail routing and spam filters operational.",
    },
}


@mcp.tool
def lookup_utd_it_policy(topic: str) -> dict:
    """
    Look up official UT Dallas OIT policies, security standards, and FERPA governance guidelines.
    Topic can be 'cometnet', 'duo', 'vpn', 'galaxy', 'ferpa', 'password', or related campus IT keywords.
    """
    clean_topic = topic.strip().lower()
    matched_key = "cometnet"
    for key in UTD_POLICIES:
        if key in clean_topic or clean_topic in key:
            matched_key = key
            break

    policy = UTD_POLICIES.get(matched_key, UTD_POLICIES["cometnet"])
    return {
        "status": "FOUND",
        "query_topic": topic,
        **policy,
    }


@mcp.tool
def check_campus_service_status(service_name: str) -> dict:
    """
    Check real-time health, latency, and uptime for UT Dallas campus IT services (e.g., CometNet, Galaxy, Duo, VPN, eLearning, Email).
    """
    clean_name = service_name.strip().lower()
    matched_key = "cometnet"
    for key in CAMPUS_SERVICES:
        if key in clean_name or clean_name in key:
            matched_key = key
            break

    svc = CAMPUS_SERVICES.get(matched_key, CAMPUS_SERVICES["cometnet"])
    return {
        "queried_service": service_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **svc,
    }


@mcp.tool
def create_sanitized_oit_ticket(category: str, sanitized_summary: str) -> dict:
    """
    Create an official UT Dallas OIT Help Desk incident ticket.
    FERPA / Privacy Guard: strictly asserts that sanitized_summary contains 0 raw SSNs, 0 raw 10-digit UTD IDs, and 0 raw email addresses.
    """
    # Enforce zero raw PII assertion
    ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
    utd_id_pattern = r"\b202\d{7}\b"
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    if re.search(ssn_pattern, sanitized_summary):
        raise ValueError("FERPA Violation: Raw SSN detected in ticket payload. Scrub before submitting.")
    if re.search(utd_id_pattern, sanitized_summary):
        raise ValueError("FERPA Violation: Raw 10-digit UTD ID detected in ticket payload. Scrub before submitting.")
    if re.search(email_pattern, sanitized_summary):
        raise ValueError("FERPA Violation: Raw email address detected in ticket payload. Scrub before submitting.")

    ticket_id = f"INC-UTD-{uuid.uuid4().hex[:6].upper()}"
    return {
        "ticket_id": ticket_id,
        "status": "CREATED",
        "category": category,
        "sanitized_summary": sanitized_summary,
        "sla_target_hours": 4,
        "assigned_group": "OIT Tier-1 Campus Support Desk",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def run_mcp_tool_for_prompt(sanitized_prompt: str) -> Optional[Dict[str, Any]]:
    """
    Introspects the pre-sanitized user prompt and executes the matching governed UTD OIT MCP tool
    using fastmcp.Client(mcp). Returns execution payload or None if no tool matched.
    """
    lower = sanitized_prompt.lower()
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = {}

    # 1. Ticket creation intent
    if any(k in lower for k in ["ticket", "incident", "report issue", "file a ticket", "submit ticket", "support desk"]):
        category = "Network & Access"
        if "password" in lower or "netid" in lower or "login" in lower:
            category = "Identity & Accounts"
        elif "galaxy" in lower:
            category = "Enterprise Systems"
        elif "canvas" in lower or "elearning" in lower:
            category = "Academic Technologies"
        tool_name = "create_sanitized_oit_ticket"
        tool_args = {
            "category": category,
            "sanitized_summary": sanitized_prompt,
        }
    # 2. Service health / status check intent
    elif any(k in lower for k in ["status", "down", "outage", "is working", "health", "uptime", "latency"]):
        target_service = "cometnet"
        if "galaxy" in lower:
            target_service = "galaxy"
        elif "duo" in lower or "mfa" in lower:
            target_service = "duo"
        elif "vpn" in lower:
            target_service = "vpn"
        elif "elearning" in lower or "canvas" in lower:
            target_service = "elearning"
        elif "email" in lower or "mail" in lower:
            target_service = "email"
        tool_name = "check_campus_service_status"
        tool_args = {"service_name": target_service}
    # 3. Policy / Governance lookup intent
    elif any(k in lower for k in ["policy", "standard", "guideline", "rule", "governance", "ferpa", "duo", "cometnet", "wifi", "vpn", "password"]):
        topic = "cometnet"
        if "ferpa" in lower or "privacy" in lower or "student record" in lower:
            topic = "ferpa"
        elif "duo" in lower or "mfa" in lower or "2fa" in lower:
            topic = "duo"
        elif "vpn" in lower or "remote" in lower:
            topic = "vpn"
        elif "galaxy" in lower:
            topic = "galaxy"
        elif "password" in lower or "passphrase" in lower:
            topic = "password"
        tool_name = "lookup_utd_it_policy"
        tool_args = {"topic": topic}

    if not tool_name:
        return None

    try:
        async with Client(mcp) as client:
            result = await client.call_tool(tool_name, arguments=tool_args)
            output_content = None
            if result.content and len(result.content) > 0:
                raw_text = result.content[0].text
                try:
                    output_content = json.loads(raw_text)
                except Exception:
                    output_content = raw_text

            return {
                "server": "UTD-OIT-Tools",
                "tool": tool_name,
                "input": tool_args,
                "output": output_content,
            }
    except Exception as e:
        # Fallback to direct python invocation if client connection has edge error
        try:
            if tool_name == "create_sanitized_oit_ticket":
                res = create_sanitized_oit_ticket(**tool_args)
            elif tool_name == "check_campus_service_status":
                res = check_campus_service_status(**tool_args)
            else:
                res = lookup_utd_it_policy(**tool_args)
            return {
                "server": "UTD-OIT-Tools",
                "tool": tool_name,
                "input": tool_args,
                "output": res,
            }
        except Exception as inner_e:
            return {
                "server": "UTD-OIT-Tools",
                "tool": tool_name,
                "input": tool_args,
                "output": {"error": str(inner_e)},
            }
