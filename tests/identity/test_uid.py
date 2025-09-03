import pytest
from src.identity.uid import (
    norm_email, norm_phone, fsa, uid_email, uid_phone, 
    uid_name_address, best_uid, norm_address
)

def test_norm_email_gmail_plus():
    """Test Gmail plus addressing removal"""
    assert norm_email("A.B+tag@Gmail.com") == "ab@gmail.com"
    assert norm_email("test+spam@gmail.com") == "test@gmail.com"

def test_norm_email_dots():
    """Test dot removal for Gmail"""
    assert norm_email("first.last@gmail.com") == "firstlast@gmail.com"
    assert norm_email("first.last@yahoo.com") == "first.last@yahoo.com"  # Not Gmail

def test_norm_email_case():
    """Test case normalization"""
    assert norm_email("Test@EXAMPLE.COM") == "test@example.com"

def test_norm_email_invalid():
    """Test invalid emails"""
    assert norm_email(None) is None
    assert norm_email("") is None
    assert norm_email("notanemail") is None

def test_norm_phone_digits():
    """Test phone normalization"""
    assert norm_phone("(555) 123-4567") == "5551234567"
    assert norm_phone("+1-555-123-4567") == "5551234567"  # Remove country code
    assert norm_phone("555.123.4567") == "5551234567"

def test_norm_phone_invalid():
    """Test invalid phones"""
    assert norm_phone(None) is None
    assert norm_phone("123") is None  # Too short
    assert norm_phone("abcdefg") is None  # No digits

def test_fsa():
    """Test Forward Sortation Area extraction"""
    assert fsa("M5V 1A1") == "M5V"
    assert fsa("90210") == "902"
    assert fsa("SW1A 1AA") == "SW1"
    assert fsa("12") is None  # Too short

def test_uid_deterministic():
    """Test UIDs are deterministic"""
    email1 = uid_email("test@example.com")
    email2 = uid_email("test@example.com")
    assert email1 == email2
    assert email1 is not None

def test_uid_name_address():
    """Test name+address UID generation"""
    uid1 = uid_name_address("John", "Smith", "M5V 1A1")
    uid2 = uid_name_address("Jane", "Smith", "M5V 1A1")  # Same first initial
    uid3 = uid_name_address("Bob", "Smith", "M5V 1A1")   # Different first initial
    uid4 = uid_name_address("John", "Smith", "M5V 1A1")  # Same as uid1
    
    assert uid1 == uid4  # Same person
    assert uid1 == uid2  # Same first initial (J)
    assert uid1 != uid3  # Different first initial (J vs B)

def test_best_uid_priority():
    """Test UID priority order"""
    # Email takes precedence
    uid = best_uid("test@example.com", "5551234567", "John", "Smith", "M5V")
    assert uid == uid_email("test@example.com")
    
    # Phone if no email
    uid = best_uid(None, "5551234567", "John", "Smith", "M5V")
    assert uid == uid_phone("5551234567")
    
    # Name+address if no email/phone
    uid = best_uid(None, None, "John", "Smith", "M5V")
    assert uid == uid_name_address("John", "Smith", "M5V")

def test_norm_address():
    """Test address normalization"""
    assert norm_address("123 Main St.") == "123 main street"
    assert norm_address("456 First Ave.") == "456 first avenue"
    assert norm_address("789 Oak Rd.") == "789 oak road"
    assert norm_address("  Multiple   Spaces  ") == "multiple spaces"
