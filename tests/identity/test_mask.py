import pytest
from src.common.mask import (
    mask_email, mask_phone, mask_address, mask_name, 
    mask_ssn, apply_masking
)

def test_mask_email():
    """Test email masking"""
    assert mask_email("john.doe@example.com") == "x***@example.com"
    assert mask_email("a@test.com") == "x***@test.com"
    assert mask_email(None) is None
    assert mask_email("invalid") == "invalid"

def test_mask_phone():
    """Test phone masking"""
    assert mask_phone("555-123-4567") == "***-***-4567"
    assert mask_phone("1234567890") == "***-***-7890"
    assert mask_phone("123") == "***"  # Too short
    assert mask_phone(None) is None

def test_mask_address():
    """Test address masking"""
    assert mask_address("123 Main St", "Toronto", "ON") == "Toronto, ON"
    assert mask_address("456 Oak Ave", None, "CA") == "***, CA"
    assert mask_address("789 Elm", None, None) == "***"

def test_mask_name():
    """Test name masking"""
    assert mask_name("John") == "J***"
    assert mask_name("alice") == "A***"
    assert mask_name("") == "***"
    assert mask_name(None) is None

def test_mask_ssn():
    """Test SSN masking"""
    assert mask_ssn("123-45-6789") == "XXX-XX-6789"
    assert mask_ssn("123456789") == "XXX-XX-6789"
    assert mask_ssn("12") == "XXX-XX-XXXX"

def test_apply_masking_viewer():
    """Test masking for viewer role"""
    data = {
        "email": "test@example.com",
        "phone": "555-123-4567",
        "first_name": "John",
        "last_name": "Doe",
        "address": "123 Main St",
        "city": "Toronto",
        "state": "ON"
    }
    
    masked = apply_masking(data, role="viewer")
    
    assert masked["email"] == "x***@example.com"
    assert masked["phone"] == "***-***-4567"
    assert masked["first_name"] == "J***"
    assert masked["last_name"] == "D***"
    assert masked["address"] == "Toronto, ON"

def test_apply_masking_admin():
    """Test no masking for admin role"""
    data = {
        "email": "test@example.com",
        "phone": "555-123-4567",
        "first_name": "John",
        "last_name": "Doe"
    }
    
    masked = apply_masking(data, role="admin")
    
    # Admin sees everything
    assert masked == data
