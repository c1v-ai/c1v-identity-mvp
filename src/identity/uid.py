import re
import hashlib
from typing import Optional

def norm_email(email: Optional[str]) -> Optional[str]:
    """Normalize email addresses"""
    if not email or not isinstance(email, str):
        return None
    
    email = email.strip().lower()
    if "@" not in email:
        return None
    
    local, _, domain = email.partition("@")
    
    # Remove everything after + (gmail style)
    local = re.sub(r"\+.*$", "", local)
    
    # Remove dots from local part (gmail style)
    if domain in ["gmail.com", "googlemail.com"]:
        local = local.replace(".", "")
    
    return f"{local}@{domain}"

def uid_email(email: Optional[str]) -> Optional[str]:
    """Generate UID from email"""
    e = norm_email(email)
    return hashlib.sha256(e.encode()).hexdigest() if e else None

def norm_phone(phone: Optional[str]) -> Optional[str]:
    """Normalize phone numbers - keep digits only"""
    if not phone or not isinstance(phone, str):
        return None
    
    # Extract digits only
    digits = re.sub(r"\D", "", phone)
    
    # Must have at least 7 digits
    if len(digits) < 7:
        return None
    
    # Remove country code 1 if present
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    
    return digits

def uid_phone(phone: Optional[str]) -> Optional[str]:
    """Generate UID from phone"""
    p = norm_phone(phone)
    return hashlib.sha256(p.encode()).hexdigest() if p else None

def fsa(postal: Optional[str]) -> Optional[str]:
    """Extract Forward Sortation Area (first 3 chars of postal)"""
    if not postal or not isinstance(postal, str):
        return None
    
    # Remove all non-alphanumeric
    clean = re.sub(r"\W+", "", postal).upper()
    
    # Return first 3 characters if available
    return clean[:3] if len(clean) >= 3 else None

def uid_name_address(first: Optional[str], last: Optional[str], postal: Optional[str]) -> Optional[str]:
    """Generate UID from name + postal"""
    if not last:
        return None
    
    # Normalize components
    last_clean = last.strip().lower()
    first_initial = (first or "").strip()[:1].lower()
    postal_fsa = fsa(postal) or ""
    
    # Create key
    key = f"{last_clean}|{first_initial}|{postal_fsa}"
    
    return hashlib.sha256(key.encode()).hexdigest()

def norm_address(address: Optional[str]) -> Optional[str]:
    """Basic address normalization"""
    if not address or not isinstance(address, str):
        return None
    
    # Basic cleanup
    addr = address.strip().lower()
    
    # Remove extra spaces
    addr = re.sub(r"\s+", " ", addr)
    
    # Standardize common abbreviations
    replacements = {
        " st ": " street ",
        " st.": " street",
        " ave ": " avenue ",
        " ave.": " avenue",
        " rd ": " road ",
        " rd.": " road",
        " dr ": " drive ",
        " dr.": " drive"
    }
    
    for old, new in replacements.items():
        addr = addr.replace(old, new)
    
    return addr

def best_uid(email: Optional[str], phone: Optional[str], first: Optional[str], 
             last: Optional[str], postal: Optional[str]) -> Optional[str]:
    """Get best available UID in priority order"""
    # Try email first
    uid = uid_email(email)
    if uid:
        return uid
    
    # Then phone
    uid = uid_phone(phone)
    if uid:
        return uid
    
    # Finally name+address
    uid = uid_name_address(first, last, postal)
    if uid:
        return uid
    
    return None
