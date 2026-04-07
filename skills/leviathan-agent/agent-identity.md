# Agent Identity Management

## Self-Registration (no account needed)

```
POST /api/v1/agents/self-register
Content-Type: application/json

{
  "email": "agent@example.com",
  "agentName": "my-staking-bot",
  "suiAddress": "0x..."  // optional
}
```

Returns an API key immediately but in `pending_verification` status. The key won't work on authenticated endpoints until the email is verified.

Rate limited: 3 registrations/hour, 10/day per IP.

Response:
```json
{
  "success": true,
  "data": {
    "apiKey": "lev_abc123...",
    "keyPrefix": "lev_abc1",
    "tier": "free",
    "status": "pending_verification",
    "rateLimits": { "rpm": 10, "rpd": 100 },
    "warning": "Store this key securely. It cannot be retrieved again."
  }
}
```

## Email Verification

```
GET /api/v1/agents/verify?token={64-char-token}
```

Called via the link in the verification email. Activates the API key.

## Key Rotation

```
POST /api/v1/agents/{id}/rotate
Authorization: Bearer {jwt}
```

Invalidates the old key and returns a new one. Use this if a key is compromised.

## List Agents

```
GET /api/v1/agents
Authorization: Bearer {jwt}
```

Returns all agent keys for the authenticated user.

## Revoke Key

```
DELETE /api/v1/agents/{id}
Authorization: Bearer {jwt}
```

Permanently deactivates an agent key.

## Behavioral Profile

```
GET /api/v1/agents/{id}/profile
Authorization: Bearer {jwt}
```

Returns 30-day behavioral analytics:
- `avgDailyQueries` — average API calls per day
- `riskAwarenessScore` — 0-100 score based on policy/terms checking frequency
- `toolBreakdown` — usage counts by endpoint
- `termShoppingCount`, `underwritingCount`, `policyCheckCount` — specific interaction counts

This data is used for tier evaluation and trust scoring.
