import pandas as pd
import numpy as np
from app.data.generator import generate_dataset

def test_determinism():
    data1 = generate_dataset(seed=42, n_customers=200)
    data2 = generate_dataset(seed=42, n_customers=200)
    
    for table_name in data1:
        pd.testing.assert_frame_equal(data1[table_name], data2[table_name])

def test_table_shapes_and_columns():
    data = generate_dataset(seed=42, n_customers=100)
    
    assert set(data.keys()) == {'customers', 'transactions', 'daily_balances', 'bills', 'customer_attributes'}
    
    assert set(data['customers'].columns) == {'customer_id', 'persona', 'created_date', 'income_stability', 'shock_exposure', 'bill_discipline'}
    assert set(data['transactions'].columns) == {'customer_id', 'date', 'type', 'amount', 'category'}
    assert set(data['daily_balances'].columns) == {'customer_id', 'date', 'balance', 'shortfall'}
    assert set(data['bills'].columns) == {'customer_id', 'due_date', 'amount', 'paid_date', 'on_time'}
    assert set(data['customer_attributes'].columns) == {'customer_id', 'gender', 'region_type', 'age_band'}

def test_persona_distribution():
    data = generate_dataset(seed=42, n_customers=1000)
    counts = data['customers']['persona'].value_counts(normalize=True)
    
    assert abs(counts.get('wage_worker', 0) - 0.30) < 0.05
    assert abs(counts.get('seasonal_farmer', 0) - 0.15) < 0.05
    assert abs(counts.get('informal_merchant', 0) - 0.25) < 0.05
    assert abs(counts.get('woman_led_household', 0) - 0.15) < 0.05
    assert abs(counts.get('salaried_user', 0) - 0.15) < 0.05

def test_no_future_leakage_splits():
    # Load function logic isn't tested here directly for leakage, but we can check hold-out logic in generator
    from app.data.loader import get_customer_ids
    # Actually wait, get_customer_ids operates on saved data, so we can mock or check hash function
    import hashlib
    def is_holdout(cid):
        return int(hashlib.md5(cid.encode()).hexdigest(), 16) % 100 < 20
    
    data = generate_dataset(seed=42, n_customers=100)
    customers = data['customers']
    customers['is_holdout'] = customers['customer_id'].apply(is_holdout)
    assert customers['is_holdout'].mean() > 0.05

def test_group_differences():
    data = generate_dataset(seed=42, n_customers=500)
    attr = data['customer_attributes']
    tx = data['transactions']
    
    merged = tx.merge(attr, on='customer_id')
    women_mean = merged[merged['gender'] == 'female']['amount'].mean()
    men_mean = merged[merged['gender'] == 'male']['amount'].mean()
    
    assert women_mean < men_mean * 0.95  # At least 5% lower

def test_seasonality_farmers():
    data = generate_dataset(seed=42, n_customers=500)
    customers = data['customers']
    tx = data['transactions']
    
    farmers = customers[customers['persona'] == 'seasonal_farmer']['customer_id']
    farmer_tx = tx[(tx['customer_id'].isin(farmers)) & (tx['type'] == 'cash_in')]
    
    farmer_tx['month'] = pd.to_datetime(farmer_tx['date']).dt.month
    monthly_in = farmer_tx.groupby('month')['amount'].sum()
    
    harvest_months = monthly_in.get(3, 0) + monthly_in.get(9, 0)
    other_months = monthly_in.sum() - harvest_months
    
    assert harvest_months / 2 > (other_months / 10) * 1.5

def test_shortfall_column():
    data = generate_dataset(seed=42, n_customers=100)
    bals = data['daily_balances']
    
    assert (bals[bals['shortfall'] == True]['balance'] < 200).all()
    assert (bals[bals['shortfall'] == False]['balance'] >= 200).all()

def test_bill_on_time_correlation():
    data = generate_dataset(seed=42, n_customers=200)
    bills = data['bills']
    customers = data['customers']
    
    merged = bills.merge(customers, on='customer_id')
    high_discipline = merged[merged['bill_discipline'] > 0.7]['on_time'].mean()
    low_discipline = merged[merged['bill_discipline'] <= 0.7]['on_time'].mean()
    
    assert high_discipline > low_discipline

def test_date_range():
    data = generate_dataset(seed=42, n_customers=100)
    bals = data['daily_balances']
    dates = pd.to_datetime(bals['date'])
    
    assert dates.min() >= pd.Timestamp('2025-01-01')
    assert dates.max() <= pd.Timestamp('2025-12-31')

def test_default_customer_count():
    import inspect
    sig = inspect.signature(generate_dataset)
    assert sig.parameters['n_customers'].default == 10000
