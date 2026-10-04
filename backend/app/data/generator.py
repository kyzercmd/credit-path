import pandas as pd
import numpy as np
from datetime import timedelta

def generate_dataset(seed: int = 42, n_customers: int = 10000) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    
    # 1. Customers
    customer_ids = [f"C{i:05d}" for i in range(1, n_customers + 1)]
    personas = ['wage_worker', 'seasonal_farmer', 'informal_merchant', 'woman_led_household', 'salaried_user']
    probs = [0.30, 0.15, 0.25, 0.15, 0.15]
    
    customer_personas = rng.choice(personas, p=probs, size=n_customers)
    
    # Base traits
    income_stability = np.zeros(n_customers)
    shock_exposure = np.zeros(n_customers)
    bill_discipline = np.zeros(n_customers)
    genders = np.array(['male'] * n_customers, dtype=object)
    regions = np.array(['urban'] * n_customers, dtype=object)
    age_bands = rng.choice(['18-25', '26-35', '36-45', '46-55', '56+'], size=n_customers)
    
    for i in range(n_customers):
        p = customer_personas[i]
        if p == 'wage_worker':
            income_stability[i] = rng.uniform(0.6, 0.9)
            shock_exposure[i] = rng.uniform(0.3, 0.6)
            bill_discipline[i] = rng.uniform(0.5, 0.8)
        elif p == 'seasonal_farmer':
            income_stability[i] = rng.uniform(0.2, 0.5)
            shock_exposure[i] = rng.uniform(0.4, 0.8)
            bill_discipline[i] = rng.uniform(0.3, 0.7)
            regions[i] = 'rural'
        elif p == 'informal_merchant':
            income_stability[i] = rng.uniform(0.4, 0.7)
            shock_exposure[i] = rng.uniform(0.5, 0.9)
            bill_discipline[i] = rng.uniform(0.4, 0.7)
        elif p == 'woman_led_household':
            income_stability[i] = rng.uniform(0.6, 0.9)
            shock_exposure[i] = rng.uniform(0.3, 0.6)
            bill_discipline[i] = rng.uniform(0.5, 0.8)
            genders[i] = 'female'
        elif p == 'salaried_user':
            income_stability[i] = rng.uniform(0.8, 1.0)
            shock_exposure[i] = rng.uniform(0.1, 0.4)
            bill_discipline[i] = rng.uniform(0.7, 1.0)
            
    # Planted fairness differences: random some other females, but keep woman_led_household 100% female
    # Let's say 20% of other personas are also female
    mask_not_wlh = customer_personas != 'woman_led_household'
    genders[mask_not_wlh] = rng.choice(['male', 'female'], p=[0.8, 0.2], size=mask_not_wlh.sum())
    
    # 2. Setup timeseries variables
    dates = pd.date_range('2025-01-01', '2025-12-31')
    n_days = len(dates)
    months = dates.month
    days = dates.day
    days_in_month = dates.days_in_month
    is_month_end = (days_in_month - days) < 5
    is_eid = np.isin(months, [4, 11])
    is_harvest = np.isin(months, [3, 9])
    
    # Pre-allocate lists for dataframes
    all_tx = []
    all_bals = []
    all_bills = []
    
    # 3. Simulate per customer
    for i in range(n_customers):
        cid = customer_ids[i]
        p = customer_personas[i]
        gender = genders[i]
        region = regions[i]
        
        # Scaling factor for women
        vol_scale = 0.8 if gender == 'female' else 1.0
        # Rural scaling
        if region == 'rural' and p != 'seasonal_farmer':
            vol_scale *= 0.9
            
        base_balance = rng.uniform(1000, 5000)
        current_balance = base_balance
        
        # We will track daily balance
        customer_bals = np.zeros(n_days)
        
        # Shocks
        has_shock = rng.random(n_days) < (0.002 * shock_exposure[i]) # Daily chance of shock expense
        income_loss = rng.random(n_days) < (0.05 / 30) # roughly 5% chance per month to start 1 week income loss
        loss_active = 0
        
        tx_dates = []
        tx_types = []
        tx_amounts = []
        tx_cats = []
        
        for d_idx in range(n_days):
            date = dates[d_idx]
            month = months[d_idx]
            
            if income_loss[d_idx]:
                loss_active = rng.integers(7, 14)
                
            has_income_loss = loss_active > 0
            if loss_active > 0:
                loss_active -= 1
                
            # Income (Cash in)
            daily_in = 0
            if not has_income_loss:
                if p == 'salaried_user' and days[d_idx] == 1:
                    daily_in = rng.normal(30000, 5000)
                elif p == 'wage_worker' and date.weekday() == 4: # Friday
                    if rng.random() < income_stability[i]:
                        daily_in = rng.normal(6000, 1000)
                elif p == 'woman_led_household' and date.weekday() == 4:
                    if rng.random() < income_stability[i]:
                        daily_in = rng.normal(5000, 1000)
                elif p == 'informal_merchant':
                    if rng.random() < income_stability[i]:
                        daily_in = rng.normal(1500, 500)
                elif p == 'seasonal_farmer':
                    if is_harvest[d_idx]:
                        if rng.random() < 0.2: # couple times a month
                            daily_in = rng.normal(15000, 5000)
                    else:
                        if rng.random() < 0.05:
                            daily_in = rng.normal(2000, 500)
                            
            # Eid bonus
            if is_eid[d_idx] and days[d_idx] == 15 and rng.random() < 0.5:
                daily_in += rng.normal(5000, 2000)
                
            daily_in *= vol_scale
            if daily_in > 0:
                tx_dates.append(date)
                tx_types.append('cash_in' if p != 'salaried_user' else 'p2p_in')
                tx_amounts.append(round(daily_in, 2))
                tx_cats.append('income')
                current_balance += daily_in
                
            # Expenses (Cash out)
            daily_out = 0
            
            # Base daily living
            if p == 'informal_merchant':
                expense_prob = 0.8
                expense_amt = 800
            elif region == 'rural':
                expense_prob = 0.3
                expense_amt = 500
            else:
                expense_prob = 0.6
                expense_amt = 1000
                
            if is_month_end[d_idx]:
                expense_prob *= 1.5
                expense_amt *= 1.2
            if is_eid[d_idx]:
                expense_prob *= 1.2
                expense_amt *= 1.5
                
            if rng.random() < expense_prob:
                amt = rng.normal(expense_amt, expense_amt*0.2) * vol_scale
                if current_balance >= amt:
                    daily_out += amt
                    tx_dates.append(date)
                    tx_types.append('merchant_payment' if rng.random() > 0.5 else 'cash_out')
                    tx_amounts.append(round(amt, 2))
                    tx_cats.append('living_expense')
                    current_balance -= amt
                    
            # Bills
            if days[d_idx] == 10: # Bill generation day
                bill_amt = rng.normal(1000, 200) * vol_scale
                due_date = date + timedelta(days=15)
                # Will they pay on time?
                pay_on_time = rng.random() < bill_discipline[i]
                if pay_on_time:
                    paid_date = due_date - timedelta(days=int(rng.integers(1, 5)))
                else:
                    paid_date = due_date + timedelta(days=int(rng.integers(1, 15)))
                    
                all_bills.append([cid, due_date, round(bill_amt, 2), paid_date, pay_on_time])
                
            # Execute bill payment if date matches any paid_date
            # Simplification: just deduct on the date we decide they pay
            # Actually, doing this sequentially is hard without a queue.
            # Instead of a queue, let's just generate the bill transactions at the end for each customer.
            
            # Shocks
            if has_shock[d_idx]:
                shock_amt = rng.normal(5000, 2000) * vol_scale
                if current_balance >= shock_amt:
                    tx_dates.append(date)
                    tx_types.append('cash_out')
                    tx_amounts.append(round(shock_amt, 2))
                    tx_cats.append('medical_emergency')
                    current_balance -= shock_amt
                    
            customer_bals[d_idx] = current_balance
            
        # Add bill transactions
        for b in all_bills:
            if b[0] == cid:
                pd_date = b[3]
                amt = b[2]
                if pd_date <= dates[-1] and pd_date >= dates[0]:
                    # adjust balance for bill payment on that date
                    # For a precise daily balance, we'd need to deduct from customer_bals from pd_date onwards
                    idx = (pd_date - dates[0]).days
                    if customer_bals[idx] >= amt:
                        tx_dates.append(pd_date)
                        tx_types.append('bill_payment')
                        tx_amounts.append(round(amt, 2))
                        tx_cats.append('utility')
                        customer_bals[idx:] -= amt
                    
        # Compile transactions
        if tx_dates:
            df_tx = pd.DataFrame({
                'customer_id': cid,
                'date': tx_dates,
                'type': tx_types,
                'amount': tx_amounts,
                'category': tx_cats
            })
            all_tx.append(df_tx)
            
        # Compile balances
        df_bal = pd.DataFrame({
            'customer_id': cid,
            'date': dates,
            'balance': np.round(customer_bals, 2),
            'shortfall': customer_bals < 200.0
        })
        all_bals.append(df_bal)

    # Combine all
    customers = pd.DataFrame({
        'customer_id': customer_ids,
        'persona': customer_personas,
        'created_date': '2024-12-01',
        'income_stability': income_stability,
        'shock_exposure': shock_exposure,
        'bill_discipline': bill_discipline
    })
    
    transactions = pd.concat(all_tx, ignore_index=True)
    daily_balances = pd.concat(all_bals, ignore_index=True)
    
    if len(all_bills) > 0:
        bills = pd.DataFrame(all_bills, columns=['customer_id', 'due_date', 'amount', 'paid_date', 'on_time'])
    else:
        bills = pd.DataFrame(columns=['customer_id', 'due_date', 'amount', 'paid_date', 'on_time'])
        
    customer_attributes = pd.DataFrame({
        'customer_id': customer_ids,
        'gender': genders,
        'region_type': regions,
        'age_band': age_bands
    })
    
    return {
        'customers': customers,
        'transactions': transactions,
        'daily_balances': daily_balances,
        'bills': bills,
        'customer_attributes': customer_attributes
    }


if __name__ == "__main__":
    from app.data.__main__ import main
    main()

