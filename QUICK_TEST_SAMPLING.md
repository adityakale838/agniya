# Quick Test: Fast Demo Mode

## Use This for IMMEDIATE Testing

### In Browser Console (http://localhost:3000/dashboard):

After uploading your CSV and configuring encryption, **BEFORE clicking "Encrypt Dataset"**, open browser console (F12) and run:

```javascript
// Modify the encrypt function to use sample_size
const originalFetch = fetch;
window.fetch = function(...args) {
  if (args[0].includes('/api/encrypt')) {
    const options = args[1];
    if (options && options.body) {
      const body = JSON.parse(options.body);
      body.sample_size = 5000;  // Only encrypt 5,000 records!
      options.body = JSON.stringify(body);
    }
  }
  return originalFetch.apply(this, args);
};
```

Then click "Encrypt Dataset" - it will only encrypt 5,000 records instead of 300,000!

## Expected Times:

| Records | Encryption Time | What to Expect |
|---------|----------------|----------------|
| 1,000 | ~5 minutes | Good for quick test |
| 5,000 | ~25 minutes | Best for demo |
| 10,000 | ~50 minutes | Maximum recommended |
| 300,000 | ~24 hours | ⚠️ DON'T DO THIS |

## Alternative: Test with Curl

```powershell
# 1. Upload file first (use UI or curl)

# 2. Encrypt with sampling
curl -X POST http://localhost:5000/api/encrypt `
  -H "Content-Type: application/json" `
  -d '{
    "filename": "online_retail_clean.csv",
    "sample_size": 5000,
    "schema": [
      {"name": "invoice_no", "encryption": "Plaintext"},
      {"name": "stock_code", "encryption": "AES-256"},
      {"name": "quantity", "encryption": "Paillier-2048"},
      {"name": "unit_price_pence", "encryption": "Paillier-2048"},
      {"name": "customer_id", "encryption": "Plaintext"},
      {"name": "total_price_pence", "encryption": "Paillier-2048"}
    ]
  }'
```

## What's Happening:

- Backend takes the **first 5,000 records** randomly sampled
- Encrypts them with your schema
- Returns success with note that sampling was used
- You can then run queries on the encrypted sample

## Why This Works for Demo:

1. **Fast enough** to see results (~25 min vs 24 hours)
2. **Representative sample** of your data
3. **Full functionality** - all queries work
4. **Realistic** - shows actual system performance

## After Encryption Completes:

Run your queries normally:
- SUM queries: ~500ms ✅
- AVG queries: ~600ms ✅  
- COUNT: <10ms ✅

All on **encrypted data** without decryption!

---

**Bottom line**: Add `sample_size: 5000` to your encrypt request for 24 hours → 25 minutes!
