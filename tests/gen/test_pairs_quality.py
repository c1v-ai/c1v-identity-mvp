"""
Test quality and constraints for generated pairs.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from gen.synth_from_schemas import SyntheticDataGenerator

class TestPairsQuality:
    """Test the quality of generated pairs."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = SyntheticDataGenerator(seed=42, locale="en_US", pii_mode="plain")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_class_balance_limits(self):
        """Test that class balance is within acceptable limits."""
        leads = self.generator.generate_leads(n=200, dup_rate=0.1)
        sales = self.generator.generate_sales(n=100, dup_rate=0.1)
        financial = self.generator.generate_financial(n=100, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        train_pairs = pairs['train']
        
        positives = len(train_pairs[train_pairs['y'] == 1])
        negatives = len(train_pairs[train_pairs['y'] == 0])
        
        # Check minimum requirements
        assert positives >= 100, f"Expected >=100 positives, got {positives}"
        assert negatives >= 500, f"Expected >=500 negatives, got {negatives}"
        
        # Check ratio limits (1:3 to 1:5)
        ratio = negatives / positives if positives > 0 else 0
        assert 3 <= ratio <= 5, f"Expected ratio 3-5, got {ratio:.2f}"
    
    def test_all_labels_valid(self):
        """Test that all labels are valid binary values."""
        leads = self.generator.generate_leads(n=200, dup_rate=0.1)
        sales = self.generator.generate_sales(n=100, dup_rate=0.1)
        financial = self.generator.generate_financial(n=100, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        
        for split_name, split_df in pairs.items():
            # Check all y values are in {0, 1}
            assert all(split_df['y'].isin([0, 1])), f"Invalid labels in {split_name}"
            
            # Check no NaN values
            assert not split_df['y'].isna().any(), f"NaN labels in {split_name}"
    
    def test_no_nan_in_key_fields(self):
        """Test that key fields have no NaN values."""
        leads = self.generator.generate_leads(n=200, dup_rate=0.1)
        sales = self.generator.generate_sales(n=100, dup_rate=0.1)
        financial = self.generator.generate_financial(n=100, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        
        # Check source datasets for NaN in key fields
        key_fields = ['email', 'first_name', 'last_name']
        
        for dataset_name, dataset in [('leads', leads), ('sales', sales), ('financial', financial)]:
            for field in key_fields:
                if field in dataset.columns:
                    nan_count = dataset[field].isna().sum()
                    assert nan_count == 0, f"Found {nan_count} NaN values in {dataset_name}.{field}"
        
        # Check pairs for NaN in key fields
        for split_name, split_df in pairs.items():
            for field in ['src_a', 'id_a', 'src_b', 'id_b', 'y']:
                nan_count = split_df[field].isna().sum()
                assert nan_count == 0, f"Found {nan_count} NaN values in pairs.{split_name}.{field}"
    
    def test_positive_pairs_quality(self):
        """Test quality of positive pairs."""
        leads = self.generator.generate_leads(n=200, dup_rate=0.1)
        sales = self.generator.generate_sales(n=100, dup_rate=0.1)
        financial = self.generator.generate_financial(n=100, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        train_pairs = pairs['train']
        positive_pairs = train_pairs[train_pairs['y'] == 1]
        
        # Check that positive pairs have valid source combinations
        valid_sources = [
            ('leads', 'sales'),
            ('sales', 'leads'),
            ('leads', 'financial'),
            ('financial', 'leads'),
            ('sales', 'financial'),
            ('financial', 'sales')
        ]
        
        for _, pair in positive_pairs.iterrows():
            source_combo = (pair['src_a'], pair['src_b'])
            assert source_combo in valid_sources, f"Invalid source combination: {source_combo}"
    
    def test_negative_pairs_quality(self):
        """Test quality of negative pairs."""
        leads = self.generator.generate_leads(n=200, dup_rate=0.1)
        sales = self.generator.generate_sales(n=100, dup_rate=0.1)
        financial = self.generator.generate_financial(n=100, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        train_pairs = pairs['train']
        negative_pairs = train_pairs[train_pairs['y'] == 0]
        
        # Check that negative pairs have valid source combinations
        valid_sources = [
            ('leads', 'sales'),
            ('sales', 'leads'),
            ('leads', 'financial'),
            ('financial', 'leads'),
            ('sales', 'financial'),
            ('financial', 'sales')
        ]
        
        for _, pair in negative_pairs.iterrows():
            source_combo = (pair['src_a'], pair['src_b'])
            assert source_combo in valid_sources, f"Invalid source combination: {source_combo}"
    
    def test_no_leakage_in_positives(self):
        """Test that positive pairs don't have empty key fields."""
        leads = self.generator.generate_leads(n=200, dup_rate=0.1)
        sales = self.generator.generate_sales(n=100, dup_rate=0.1)
        financial = self.generator.generate_financial(n=100, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        train_pairs = pairs['train']
        positive_pairs = train_pairs[train_pairs['y'] == 1]
        
        # Check that positive pairs have non-empty key fields in source records
        for _, pair in positive_pairs.iterrows():
            # Get source records
            if pair['src_a'] == 'leads':
                record_a = leads[leads['id'] == pair['id_a']].iloc[0] if len(leads[leads['id'] == pair['id_a']]) > 0 else None
            elif pair['src_a'] == 'sales':
                record_a = sales[sales['id'] == pair['id_a']].iloc[0] if len(sales[sales['id'] == pair['id_a']]) > 0 else None
            else:  # financial
                record_a = financial[financial['id'] == pair['id_a']].iloc[0] if len(financial[financial['id'] == pair['id_a']]) > 0 else None
            
            if pair['src_b'] == 'leads':
                record_b = leads[leads['id'] == pair['id_b']].iloc[0] if len(leads[leads['id'] == pair['id_b']]) > 0 else None
            elif pair['src_b'] == 'sales':
                record_b = sales[sales['id'] == pair['id_b']].iloc[0] if len(sales[sales['id'] == pair['id_b']]) > 0 else None
            else:  # financial
                record_b = financial[financial['id'] == pair['id_b']].iloc[0] if len(financial[financial['id'] == pair['id_b']]) > 0 else None
            
            # Skip if records not found (shouldn't happen but handle gracefully)
            if record_a is None or record_b is None:
                continue
                
            # Check key fields are not empty
            key_fields = ['email', 'first_name', 'last_name']
            for field in key_fields:
                if field in record_a.index:
                    assert pd.notna(record_a[field]) and str(record_a[field]).strip() != "", \
                        f"Empty key field {field} in positive pair source A"
                if field in record_b.index:
                    assert pd.notna(record_b[field]) and str(record_b[field]).strip() != "", \
                        f"Empty key field {field} in positive pair source B"
    
    def test_split_ratios(self):
        """Test that train/validation/test splits have correct ratios."""
        leads = self.generator.generate_leads(n=200, dup_rate=0.1)
        sales = self.generator.generate_sales(n=100, dup_rate=0.1)
        financial = self.generator.generate_financial(n=100, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        
        total_pairs = sum(len(split_df) for split_df in pairs.values())
        train_count = len(pairs['train'])
        val_count = len(pairs['validation'])
        test_count = len(pairs['test'])
        
        # Check approximate ratios (70/15/15)
        if total_pairs > 0:
            train_ratio = train_count / total_pairs
            val_ratio = val_count / total_pairs
            test_ratio = test_count / total_pairs
            
            assert abs(train_ratio - 0.7) < 0.1, f"Train ratio {train_ratio:.2f} not close to 0.7"
            assert abs(val_ratio - 0.15) < 0.1, f"Validation ratio {val_ratio:.2f} not close to 0.15"
            assert abs(test_ratio - 0.15) < 0.1, f"Test ratio {test_ratio:.2f} not close to 0.15"
    
    def test_unique_pairs(self):
        """Test that pairs are unique within each split."""
        leads = self.generator.generate_leads(n=200, dup_rate=0.1)
        sales = self.generator.generate_sales(n=100, dup_rate=0.1)
        financial = self.generator.generate_financial(n=100, dup_rate=0.1)
        
        pairs = self.generator.build_pairs(leads, sales, financial, overlap=0.4)
        
        for split_name, split_df in pairs.items():
            # Create a unique identifier for each pair
            if len(split_df) > 0:
                pair_ids = split_df.apply(lambda x: f"{x['src_a']}:{x['id_a']}_{x['src_b']}:{x['id_b']}", axis=1)
                assert len(pair_ids) == len(pair_ids.unique()), f"Duplicate pairs found in {split_name}"
    
    def test_data_types(self):
        """Test that generated data has correct types."""
        leads = self.generator.generate_leads(n=100, dup_rate=0.1)
        sales = self.generator.generate_sales(n=50, dup_rate=0.1)
        financial = self.generator.generate_financial(n=50, dup_rate=0.1)
        
        # Check string fields
        string_fields = ['id', 'email', 'phone', 'first_name', 'last_name', 'city', 'state', 'country']
        for dataset in [leads, sales, financial]:
            for field in string_fields:
                if field in dataset.columns:
                    assert dataset[field].dtype == 'object', f"Field {field} should be string type"
        
        # Check numeric fields
        assert pd.api.types.is_numeric_dtype(sales['order_value']), "order_value should be numeric"
        assert pd.api.types.is_numeric_dtype(financial['amount']), "amount should be numeric"
        
        # Check datetime fields
        assert pd.api.types.is_datetime64_any_dtype(leads['created_at']), "created_at should be datetime"
        assert pd.api.types.is_datetime64_any_dtype(sales['order_date']), "order_date should be datetime"
        assert pd.api.types.is_datetime64_any_dtype(financial['invoice_date']), "invoice_date should be datetime"
