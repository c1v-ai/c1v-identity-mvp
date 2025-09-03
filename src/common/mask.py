import re
from typing import Optional, Dict, Any
import yaml
from pathlib import Path
import pandas as pd

def load_masking_config(path: str = "configs/rbac.yaml") -> Dict[str, str]:
    """Load masking patterns from RBAC config"""
    config = yaml.safe_load(Path(path).read_text())
    return config.get("masking", {})

def mask_email(email: Optional[str], pattern: str = "x***@{domain}") -> Optional[str]:
    """Mask email address"""
    if not email or "@" not in email:
        return email
    
    local, _, domain = email.partition("@")
    
    if "{domain}" in pattern:
        return pattern.replace("{domain}", domain)
    else:
        # Default: show first char + domain
        return f"{local[0]}***@{domain}" if local else f"***@{domain}"

def mask_phone(phone: Optional[str], pattern: str = "***-***-{last4}") -> Optional[str]:
    """Mask phone number"""
    if not phone:
        return phone
    
    # Extract digits
    digits = re.sub(r"\D", "", str(phone))
    
    if len(digits) < 4:
        return "***"
    
    if "{last4}" in pattern:
        return pattern.replace("{last4}", digits[-4:])
    else:
        # Default: show last 4
        return f"***-***-{digits[-4:]}"

def mask_address(address: Optional[str], city: Optional[str] = None, 
                 region: Optional[str] = None, pattern: str = "{city}, {region}") -> Optional[str]:
    """Mask street address"""
    if not address:
        return address
    
    # If pattern uses city/region
    if "{city}" in pattern or "{region}" in pattern:
        result = pattern
        result = result.replace("{city}", city or "***")
        result = result.replace("{region}", region or "***")
        return result if result != "***, ***" else "***"
    else:
        # Default: hide street details
        if city or region:
            parts = []
            if city:
                parts.append(city)
            if region:
                parts.append(region)
            return ", ".join(parts)
        else:
            return "***"

def mask_name(name: Optional[str], pattern: str = "{first_initial}***") -> Optional[str]:
    """Mask name"""
    if name is None:
        return None
    
    name = str(name).strip()
    
    if not name:  # Empty string after stripping
        return "***"
    
    if "{first_initial}" in pattern:
        return pattern.replace("{first_initial}", name[0].upper())
    else:
        # Default: show first initial
        return f"{name[0].upper()}***"

def mask_ssn(ssn: Optional[str], pattern: str = "XXX-XX-{last4}") -> Optional[str]:
    """Mask SSN"""
    if not ssn:
        return ssn
    
    # Extract digits
    digits = re.sub(r"\D", "", str(ssn))
    
    if len(digits) < 4:
        return "XXX-XX-XXXX"
    
    if "{last4}" in pattern:
        return pattern.replace("{last4}", digits[-4:])
    else:
        return f"XXX-XX-{digits[-4:]}"

def apply_masking(data: Dict[str, Any], role: str = "viewer", 
                  masking_config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Apply masking based on role"""
    # Load RBAC config
    rbac = yaml.safe_load(Path("configs/rbac.yaml").read_text())
    
    # Check if role can view PII
    role_config = rbac["roles"].get(role, {})
    if role_config.get("pii_view", False):
        return data  # No masking for admins
    
    # Get masking patterns
    patterns = masking_config or rbac.get("masking", {})
    
    # Apply masking
    masked = data.copy()
    
    # Email fields
    for field in ["email", "customer_email", "cust_email"]:
        if field in masked and masked[field]:
            masked[field] = mask_email(masked[field], patterns.get("email", "x***@{domain}"))
    
    # Phone fields
    for field in ["phone", "customer_phone", "cust_phone"]:
        if field in masked and masked[field]:
            masked[field] = mask_phone(masked[field], patterns.get("phone", "***-***-{last4}"))
    
    # Address fields
    if "address" in masked and masked["address"]:
        masked["address"] = mask_address(
            masked["address"], 
            masked.get("city"), 
            masked.get("region") or masked.get("state"),
            patterns.get("address", "{city}, {region}")
        )
    
    # Name fields
    for field in ["first_name", "last_name", "first", "last"]:
        if field in masked and masked[field]:
            masked[field] = mask_name(masked[field], patterns.get("name", "{first_initial}***"))
    
    # SSN if present
    if "ssn" in masked and masked["ssn"]:
        masked["ssn"] = mask_ssn(masked["ssn"], patterns.get("ssn", "XXX-XX-{last4}"))
    
    return masked

def mask_dataframe(df: pd.DataFrame, role: str = "viewer") -> pd.DataFrame:
    """Apply masking to entire dataframe"""
    import pandas as pd
    
    # Load RBAC config
    rbac = yaml.safe_load(Path("configs/rbac.yaml").read_text())
    
    # Check if role can view PII
    role_config = rbac["roles"].get(role, {})
    if role_config.get("pii_view", False):
        return df  # No masking for admins
    
    # Create copy
    masked_df = df.copy()
    
    # Get masking patterns
    patterns = rbac.get("masking", {})
    
    # Apply column-wise masking
    for col in masked_df.columns:
        col_lower = col.lower()
        
        if "email" in col_lower:
            masked_df[col] = masked_df[col].apply(lambda x: mask_email(x, patterns.get("email", "x***@{domain}")))
        elif "phone" in col_lower or "mobile" in col_lower:
            masked_df[col] = masked_df[col].apply(lambda x: mask_phone(x, patterns.get("phone", "***-***-{last4}")))
        elif col_lower in ["first_name", "last_name", "first", "last"]:
            masked_df[col] = masked_df[col].apply(lambda x: mask_name(x, patterns.get("name", "{first_initial}***")))
        elif col_lower == "address":
            # For address, we need city and state columns
            city_col = next((c for c in df.columns if "city" in c.lower()), None)
            state_col = next((c for c in df.columns if "state" in c.lower() or "region" in c.lower()), None)
            
            if city_col and state_col:
                masked_df[col] = df.apply(
                    lambda row: mask_address(row[col], row.get(city_col), row.get(state_col), patterns.get("address", "{city}, {region}")),
                    axis=1
                )
            else:
                masked_df[col] = masked_df[col].apply(lambda x: "***" if x else x)
    
    return masked_df
