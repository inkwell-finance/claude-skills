---
name: leviathan-agent
description: Interact with the Inkwell IKA Staking Agent API — compute optimal allocations, build stake/unstake transactions, score validators, manage API keys, and rebalance positions. Use when the user wants to stake IKA, analyze validators, or build on the Inkwell agent API.
user-invocable: true
---

# Inkwell Agent API Skill

## What this Skill is for

Use this Skill when the user asks for:
- Staking IKA tokens (compute allocation, build transactions)
- Validator analysis (scoring, APY history, delegator lists)
- Rebalancing existing staking positions
- Registering for or managing Inkwell API keys
- Querying IKA network state (epoch, price, validators)
- Integrating with the Inkwell agent API from code

## API Base URLs

- **Agent API** (requires API key): `https://backend.inkwell.finance/api/v1/ika/agent`
- **Public API** (no auth): `https://backend.inkwell.finance/api/v1/ika`
- **Agent Identity**: `https://backend.inkwell.finance/api/v1/agents`

## Authentication

Agent endpoints require `X-API-Key` header. Get a key via self-registration:

```bash
curl -X POST https://backend.inkwell.finance/api/v1/agents/self-register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "agentName": "my-agent"}'
```

Key must be verified via email before use.

## Operating procedure

### 1. Classify the request

| User wants to... | Use these endpoints |
|-------------------|---------------------|
| Stake IKA | `/allocate` -> `/tx/stake` |
| Unstake IKA | `/tx/unstake` (then `/tx/withdraw` after epoch) |
| See best validators | `/validators/scored` |
| Rebalance positions | `/rebalance-plan` (requires builder+ tier) |
| Check their tier/limits | `/usage` |
| Get an API key | `/agents/self-register` |
| Monitor network | Public: `/epoch`, `/price`, `/validators` |

### 2. Execute the workflow

**Staking flow** (most common):
1. Call `POST /allocate` with amount and maxValidators
2. For each allocation in the response, call `POST /tx/stake` with validatorId and amount
3. Return the Move call params to the user for signing

**Rebalance flow**:
1. Check tier via `GET /usage` — rebalancing requires builder or pro
2. Call `POST /rebalance-plan` with current positions
3. Present the steps (unstake first, wait epoch, then stake to new validators)

### 3. Key constraints

- Amounts are in **MIST** (1 IKA = 1,000,000,000 MIST / 1e9)
- Minimum stake: 1 IKA (1000000000 MIST)
- Unstaking requires waiting 1 epoch (~24 hours) before withdrawal
- Free tier only sees top 10 validators; builder sees top 25
- Rebalance endpoint returns 403 for free tier agents

### 4. Error handling

All errors return `{ error, message, status }`. Common cases:
- `401` — missing or invalid API key
- `403` — tier too low for endpoint
- `429` — rate limited (check `Retry-After` header)
- `503` — IKA store not initialized (backend still syncing)

## Progressive disclosure

- IKA staking details: [ika-staking.md](ika-staking.md)
- Agent identity management: [agent-identity.md](agent-identity.md)
- Full staking example: [examples/stake-flow.md](examples/stake-flow.md)
- Registration example: [examples/register-agent.md](examples/register-agent.md)
