# Example: Register an Agent and Make First Call

## 1. Self-register

```bash
curl -X POST https://backend.inkwell.finance/api/v1/agents/self-register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "devbot@example.com",
    "agentName": "portfolio-rebalancer"
  }'
```

Response:
```json
{
  "success": true,
  "data": {
    "apiKey": "lev_7f3a9b2c...",
    "keyPrefix": "lev_7f3a",
    "tier": "free",
    "status": "pending_verification",
    "rateLimits": { "rpm": 10, "rpd": 100 },
    "warning": "Store this key securely. It cannot be retrieved again. Check your email to verify and activate it."
  }
}
```

**Save `apiKey` immediately.** It cannot be retrieved later.

## 2. Verify email

Click the link in the verification email. The API key becomes active.

## 3. Test the key

```bash
curl https://backend.inkwell.finance/api/v1/ika/agent/usage \
  -H "X-API-Key: lev_7f3a9b2c..."
```

Expected:
```json
{
  "tier": "free",
  "limits": { "rpm": 10, "rpd": 100 }
}
```

## 4. Get scored validators

```bash
curl https://backend.inkwell.finance/api/v1/ika/agent/validators/scored \
  -H "X-API-Key: lev_7f3a9b2c..."
```

Free tier returns the top 10 validators by composite score.

## 5. Check network health

No API key needed for public endpoints:

```bash
curl https://backend.inkwell.finance/api/v1/ika/health
curl https://backend.inkwell.finance/api/v1/ika/epoch
curl https://backend.inkwell.finance/api/v1/ika/price
```
