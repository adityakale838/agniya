"""
Synthetic retail-bank customers for the banking demo (data/bank_customers.csv). Every value is generated:
no real customer, bank or account. Seeded, so the file is the same on every run.

    envb\\Scripts\\python.exe tools\\make_bank_data.py [rows]      # default 2,000

Columns: customer_id, region, segment, product, age, credit_score (300-850), risk_band (A best ... E),
balance (GBP), loan_amount (outstanding, 0 without a loan), monthly_spend, days_past_due (0/30/60/90),
default_flag (1 = defaulted). Risk follows credit score; balances, loans and spend follow segment.
"""
import csv
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = ['London', 'South East', 'Midlands', 'North West', 'Scotland', 'Wales']
SEGMENTS = {'Retail': 0.62, 'Premier': 0.18, 'Business': 0.14, 'Wealth': 0.06}  # share of customers
WEALTH = {'Retail': 1.0, 'Premier': 4.0, 'Business': 6.0, 'Wealth': 15.0}  # scales balance, loans, spend
PRODUCTS = ['Current', 'Savings', 'Mortgage', 'Credit Card', 'Personal Loan']
LOAN_SIZE = {'Mortgage': 180_000, 'Personal Loan': 9_000, 'Credit Card': 2_500}  # typical outstanding


def band(score):
    return 'A' if score >= 750 else 'B' if score >= 680 else 'C' if score >= 600 else 'D' if score >= 520 else 'E'


def main(rows=2000):
    rnd = random.Random(2026)
    out = []
    for i in range(rows):
        segment = rnd.choices(list(SEGMENTS), weights=SEGMENTS.values())[0]
        w = WEALTH[segment]
        product = rnd.choices(PRODUCTS, weights=[30, 25, 15, 20, 10])[0]
        age = min(85, max(18, int(rnd.gauss(44 if segment != 'Retail' else 38, 13))))
        score = min(850, max(300, int(rnd.gauss(690 + 15 * (w > 1), 85))))
        loan = round(rnd.lognormvariate(0, 0.5) * LOAN_SIZE[product] * (w ** 0.5), 2) if product in LOAN_SIZE else 0.0
        p_default = {'A': 0.004, 'B': 0.012, 'C': 0.035, 'D': 0.09, 'E': 0.2}[band(score)] * (2 if loan else 0.3)
        default = int(rnd.random() < p_default)
        dpd = 90 if default else rnd.choices([0, 30, 60], weights=[92, 6, 2])[0] if loan else 0
        out.append({
            'customer_id': f'C{100000 + i}', 'region': rnd.choice(REGIONS), 'segment': segment, 'product': product,
            'age': age, 'credit_score': score, 'risk_band': band(score),
            'balance': round(rnd.lognormvariate(7.6, 1.0) * w, 2), 'loan_amount': loan,
            'monthly_spend': round(rnd.lognormvariate(7.0, 0.5) * w ** 0.6, 2),
            'days_past_due': dpd, 'default_flag': default,
        })
    path = os.path.join(ROOT, 'data', 'bank_customers.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    print(f'wrote {path} ({rows} rows)')


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
