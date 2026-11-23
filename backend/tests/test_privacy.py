import pytest
from backend.app.privacy import redact_pii


def test_redact_utd_id():
    text = "My student ID is 2025123456 and I need access to CometNet."
    report = redact_pii(text)
    assert report.redacted_count == 1
    assert "2025123456" not in report.sanitized_text
    assert "[REDACTED_UTD_ID]" in report.sanitized_text
    assert report.entities[0].entity_type == "UTD_ID"
    assert report.entities[0].text == "2025123456"


def test_redact_ssn():
    text = "Student SSN on file is 123-45-6789."
    report = redact_pii(text)
    assert report.redacted_count == 1
    assert "123-45-6789" not in report.sanitized_text
    assert "[REDACTED_SSN]" in report.sanitized_text
    assert report.entities[0].entity_type == "SSN"


def test_redact_email():
    text = "Please reach out to temoc@utdallas.edu for enrollment queries."
    report = redact_pii(text)
    assert report.redacted_count == 1
    assert "temoc@utdallas.edu" not in report.sanitized_text
    assert "[REDACTED_EMAIL]" in report.sanitized_text
    assert report.entities[0].entity_type == "EMAIL"


def test_redact_phone():
    text = "Call the OIT Help Desk at 972-883-2911 or (972) 883-2911."
    report = redact_pii(text)
    assert report.redacted_count == 2
    assert "972-883-2911" not in report.sanitized_text
    assert "(972) 883-2911" not in report.sanitized_text
    assert "[REDACTED_PHONE]" in report.sanitized_text


def test_redact_multi_entity():
    text = (
        "Student Temoc (ID: 2021987654, SSN: 987-65-4321, email: temoc@utdallas.edu, "
        "phone: 972-555-0199) requested financial aid records."
    )
    report = redact_pii(text)
    assert report.redacted_count == 4
    assert "2021987654" not in report.sanitized_text
    assert "987-65-4321" not in report.sanitized_text
    assert "temoc@utdallas.edu" not in report.sanitized_text
    assert "972-555-0199" not in report.sanitized_text
    assert "[REDACTED_UTD_ID]" in report.sanitized_text
    assert "[REDACTED_SSN]" in report.sanitized_text
    assert "[REDACTED_EMAIL]" in report.sanitized_text
    assert "[REDACTED_PHONE]" in report.sanitized_text


def test_clean_prompt():
    text = "How do I reset my NetID password on the UTD self-service portal?"
    report = redact_pii(text)
    assert report.redacted_count == 0
    assert report.sanitized_text == text
    assert len(report.entities) == 0


def test_empty_prompt():
    report = redact_pii("")
    assert report.redacted_count == 0
    assert report.sanitized_text == ""
    assert report.entities == []
