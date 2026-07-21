"""PII detection and redaction tests."""

from eiye_db.pii import luhn_valid, redact_structure, redact_text


def test_redacts_email():
    text, counts = redact_text("contact alice@example.com now")
    assert text == "contact [REDACTED:email] now"
    assert counts == {"email": 1}


def test_redacts_ssn():
    text, counts = redact_text("SSN: 123-45-6789")
    assert "[REDACTED:ssn]" in text
    assert counts == {"ssn": 1}


def test_redacts_phone():
    text, _ = redact_text("call (617) 555-1234 or 617-555-9876")
    assert text.count("[REDACTED:phone]") == 2


def test_redacts_valid_credit_card_only():
    # 4532015112830366 passes Luhn; 1234567812345678 does not
    text, counts = redact_text("card 4532015112830366 vs 1234567812345678")
    assert "[REDACTED:credit_card]" in text
    assert "1234567812345678" in text
    assert counts == {"credit_card": 1}


def test_luhn():
    assert luhn_valid("4532015112830366")
    assert not luhn_valid("1234567812345678")


def test_redacts_ipv4():
    text, _ = redact_text("host 192.168.1.100 responded")
    assert text == "host [REDACTED:ipv4] responded"


def test_clean_text_untouched():
    text, counts = redact_text("nothing sensitive here")
    assert text == "nothing sensitive here"
    assert counts == {}


def test_redacts_pii_in_dict_keys():
    obj = {"alice@example.com": {"balance": 100}}
    redacted, counts = redact_structure(obj)
    assert "alice@example.com" not in redacted
    assert redacted["[REDACTED:email]"] == {"balance": 100}
    assert counts == {"email": 1}


def test_redacts_numeric_credit_card():
    # card number stored as an int (e.g. a bigint column)
    redacted, counts = redact_structure([{"card": 4532015112830366}])
    assert redacted[0]["card"] == "[REDACTED:credit_card]"
    assert counts == {"credit_card": 1}


def test_bool_and_plain_numbers_untouched():
    redacted, counts = redact_structure([{"active": True, "count": 42, "ratio": 3.14}])
    assert redacted[0] == {"active": True, "count": 42, "ratio": 3.14}
    assert counts == {}


def test_redact_structure_recurses():
    obj = {
        "user": {"email": "bob@corp.io", "name": "Bob"},
        "notes": ["ip is 10.0.0.1", 42, None],
    }
    redacted, counts = redact_structure(obj)
    assert redacted["user"]["email"] == "[REDACTED:email]"
    assert redacted["user"]["name"] == "Bob"
    assert redacted["notes"][0] == "ip is [REDACTED:ipv4]"
    assert redacted["notes"][1] == 42
    assert counts == {"email": 1, "ipv4": 1}
