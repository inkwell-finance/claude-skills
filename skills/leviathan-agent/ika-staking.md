# IKA Staking Endpoints

## Scored Validators

```
GET /api/v1/ika/agent/validators/scored
```

Returns validators ranked by a composite score (APY, uptime, commission). Results are tier-filtered unless you pass specific `validators` IDs.

Response shape:
```json
{
  "validators": [
    { "validatorId": "0x...", "name": "ValidatorA", "score": 87.5, "apy": 8.2, "commissionRate": 0.05, "totalStake": "500000000000" }
  ],
  "epoch": 142,
  "dataAgeSeconds": 30,
  "tierDetail": "free"
}
```

## Allocate

```
POST /api/v1/ika/agent/allocate
Body: { "amount": "10000000000", "maxValidators": 5 }
```

Computes optimal stake distribution. Returns allocations with weights and a projected weighted APY.

Response shape:
```json
{
  "allocations": [
    { "validatorId": "0x...", "amount": "5000000000", "weight": 0.5 },
    { "validatorId": "0x...", "amount": "3000000000", "weight": 0.3 },
    { "validatorId": "0x...", "amount": "2000000000", "weight": 0.2 }
  ],
  "totalProjectedApy": 8.1
}
```

## Transaction Builders

All tx endpoints return Move call parameters. The caller constructs a `TransactionBlock`, adds the move call, signs, and submits.

### Stake
```
POST /api/v1/ika/agent/tx/stake
Body: { "validatorId": "0x...", "amount": "5000000000" }
```

Optional fields: `sender` (Sui address), `coins` (specific coin objects to use).

### Unstake
```
POST /api/v1/ika/agent/tx/unstake
Body: { "stakedIkaId": "0x..." }
```

After unstaking, the position enters a 1-epoch (~24h) cooldown.

### Withdraw
```
POST /api/v1/ika/agent/tx/withdraw
Body: { "stakedIkaId": "0x..." }
```

Only callable after the cooldown period completes. Returns IKA tokens to the wallet.

## Rebalance Plan

```
POST /api/v1/ika/agent/rebalance-plan
```

**Requires builder or pro tier.** Takes current positions and returns optimized steps:

```json
{
  "positions": [
    { "stakedIkaId": "0x...", "validatorId": "0x...", "principal": "5000000000" }
  ],
  "maxTargets": 5
}
```

Response includes:
- `currentPositions` — current allocations with APY
- `steps` — ordered array of `{ action: "unstake"|"stake", validator, amount, requiresEpochWait, order }`
- `summary` — current vs projected weighted APY, estimated epochs to complete

## Delegators

```
GET /api/v1/ika/agent/delegators/{validatorId}
```

Returns delegator list for a validator. May return `syncing: true` with empty results if data is still being indexed.

## Usage

```
GET /api/v1/ika/agent/usage
```

Returns current agent tier and rate limits: `{ tier, limits: { rpm, rpd } }`.
