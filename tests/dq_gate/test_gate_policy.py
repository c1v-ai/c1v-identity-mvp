import pytest
from src.dq_gate.gate import decide_action, load_policy

def test_red_block_in_prod():
    """RED should BLOCK in prod"""
    policy = load_policy()
    assert decide_action("RED", "prod", policy) == "BLOCK"

def test_red_warn_in_week1():
    """RED should WARN in prod_week1"""
    policy = load_policy()
    assert decide_action("RED", "prod_week1", policy) == "WARN"

def test_amber_block_in_staging():
    """AMBER should BLOCK in staging"""
    policy = load_policy()
    assert decide_action("AMBER", "staging", policy) == "BLOCK"

def test_amber_warn_in_prod():
    """AMBER should WARN in prod"""
    policy = load_policy()
    assert decide_action("AMBER", "prod", policy) == "WARN"

def test_green_pass_everywhere():
    """GREEN should PASS in all environments"""
    policy = load_policy()
    for env in ["staging", "prod_week1", "prod"]:
        assert decide_action("GREEN", env, policy) == "PASS"
