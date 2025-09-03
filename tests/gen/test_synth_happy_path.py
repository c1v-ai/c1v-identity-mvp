"""
Test happy path for synthetic data generation.
"""

import pytest
import pandas as pd
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from gen.synth_from_schemas import SyntheticDataGenerator

class TestSyntheticDataGenerator:
    """Test the synthetic data generator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = SyntheticDataGenerator(seed=42, locale="en_US", pii_mode="plain")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        assert self.generator.seed == 42
        assert self.generator.locale == "en_US"
        assert self.generator.pii_mode == "plain"
        assert self.generator.faker is not None
    
    def test_generate_leads_small(self):
        """Test generating a small number of leads."""
        leads = self.generator.generate_leads(n=100, dup_rate=0.1)
        
        assert isinstance(leads, pd.DataFrame)
        assert len(leads) >= 100  # May be more due to duplicates
        assert all(col in leads.columns for col in [
            'id', 'email', 'phone', 'first_name', 'last_name', 'company',
            'address', 'city', 'state', 'zip', 'country', 'source', 'created_at'
        ])
        
        # Check IDs are unique
        assert leads['id'].nunique() == len(leads)
        
        # Check no NaN in key fields
        assert not leads['email'].isna().any()
        assert not leads['first_name'].isna().any()
        assert not leads['last_name'].isna().any()
    
    def test_generate_sales_small(self):
        """Test generating a small number of sales records."""
        sales = self.generator.generate_sales(n=50, dup_rate=0.1)
        
        assert isinstance(sales, pd.DataFrame)
        assert len(sales) >= 50
        assert all(col in sales.columns for col in [
            'id', 'email', 'phone', 'first_name', 'last_name', 'account',
            'address', 'city', 'state', 'zip', 'country', 'order_id', 'order_date', 'order_value'
        ])
        
        # Check IDs are unique
        assert sales['id'].nunique() == len(sales)
        
        # Check order values are reasonable
        assert sales['order_value'].min() >= 100
        assert sales['order_value'].max() <= 100000
    
    def test_generate_financial_small(self):
        """Test generating a small number of financial records."""
        financial = self.generator.generate_financial(n=50, dup_rate=0.1)
        
        assert isinstance(financial, pd.DataFrame)
        assert len(financial) >= 50
        assert all(col in financial.columns for col in [
            'id', 'email', 'phone', 'first_name', 'last_name', 'account',
            'billing_address', 'city', 'state', 'zip', 'country', 'invoice_id', 'invoice_date', 'amount'
        ])
        
        # Check IDs are unique
        assert financial['id'].nunique() == len(financial)
        
        # Check amounts are reasonable
        assert financial['amount'].min() >= 10
        assert financial['amount'].max() <= 20000
    
    def test_build_pairs(self):
        """Test building pairs from generated data."""
        leads = self.generator.generate_leads(n=100, dup_rate=0.1)
        sales = self.generator.generate_sales(n=50, dup_rate=0.1)
        financial = self.generator.generate_financial(n=50, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        
        assert isinstance(pairs, dict)
        assert 'train' in pairs
        assert 'validation' in pairs
        assert 'test' in pairs
        
        # Check all pairs have required columns
        for split_name, split_df in pairs.items():
            assert all(col in split_df.columns for col in ['src_a', 'id_a', 'src_b', 'id_b', 'y'])
            assert len(split_df) > 0
        
        # Check class balance
        train_pairs = pairs['train']
        positives = len(train_pairs[train_pairs['y'] == 1])
        negatives = len(train_pairs[train_pairs['y'] == 0])
        
        assert positives >= 10  # At least some positives
        assert negatives >= 30  # At least some negatives
    
    def test_validation(self):
        """Test data validation."""
        leads = self.generator.generate_leads(n=100, dup_rate=0.1)
        sales = self.generator.generate_sales(n=50, dup_rate=0.1)
        financial = self.generator.generate_financial(n=50, dup_rate=0.1)
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        
        summary = self.generator.validate_data(leads, sales, financial, pairs)
        
        assert isinstance(summary, dict)
        assert 'status' in summary
        assert 'record_counts' in summary
        assert 'pairs_counts' in summary
        assert 'class_balance' in summary
        assert 'validation_checks' in summary
        
        # Check record counts
        assert summary['record_counts']['leads'] >= 100
        assert summary['record_counts']['sales'] >= 50
        assert summary['record_counts']['financial'] >= 50
        
        # Check pairs counts
        assert summary['pairs_counts']['train'] > 0
        assert summary['pairs_counts']['validation'] > 0
        assert summary['pairs_counts']['test'] > 0
    
    def test_pii_hashing(self):
        """Test PII hashing mode."""
        hashed_generator = SyntheticDataGenerator(seed=42, locale="en_US", pii_mode="hashed")
        
        # Test hashing function
        original = "test@example.com"
        hashed = hashed_generator.hash_pii(original)
        
        assert hashed != original
        assert len(hashed) == 16  # First 16 chars of SHA256
        assert hashed.isalnum()  # Should be hex string
    
    def test_noise_injection(self):
        """Test noise injection functions."""
        # Test case variations
        result = self.generator.inject_noise("test", "case")
        assert result in ["test", "TEST", "Test"]
        
        # Test whitespace variations
        result = self.generator.inject_noise("test", "whitespace")
        assert result in ["test", "test ", " test"]
        
        # Test typo simulation
        result = self.generator.inject_noise("test", "typo")
        # Should either be unchanged or have 1-2 character changes
        assert result == "test" or len(result) == 4
    
    def test_locale_specific_generation(self):
        """Test locale-specific generation."""
        # Test US locale
        us_generator = SyntheticDataGenerator(seed=42, locale="en_US", pii_mode="plain")
        us_phone = us_generator.generate_phone("US")
        us_zip = us_generator.generate_zip("US")
        
        assert us_phone.startswith("(")
        assert len(us_zip) in [5, 10]  # 12345 or 12345-6789
        
        # Test CA locale
        ca_generator = SyntheticDataGenerator(seed=42, locale="en_CA", pii_mode="plain")
        ca_phone = ca_generator.generate_phone("CA")
        ca_zip = ca_generator.generate_zip("CA")
        
        assert ca_phone.startswith("+1-")
        assert len(ca_zip) == 7  # A1A 1A1 format
        assert " " in ca_zip

def test_cli_integration():
    """Test CLI integration with small dataset."""
    # This test would require mocking or actual file I/O
    # For now, just test that the main function can be imported
    from gen.synth_from_schemas import main
    assert callable(main)
