# Example: Full Staking Flow

This example walks through staking 10 IKA across optimal validators.

## 1. Get optimal allocation

```bash
curl -X POST https://backend.inkwell.finance/api/v1/ika/agent/allocate \
  -H "X-API-Key: lev_your_key" \
  -H "Content-Type: application/json" \
  -d '{"amount": "10000000000", "maxValidators": 3}'
```

Response:
```json
{
  "allocations": [
    { "validatorId": "0xaaa...", "amount": "5000000000", "weight": 0.5 },
    { "validatorId": "0xbbb...", "amount": "3000000000", "weight": 0.3 },
    { "validatorId": "0xccc...", "amount": "2000000000", "weight": 0.2 }
  ],
  "totalProjectedApy": 8.1
}
```

## 2. Build stake transactions

For each allocation:

```bash
curl -X POST https://backend.inkwell.finance/api/v1/ika/agent/tx/stake \
  -H "X-API-Key: lev_your_key" \
  -H "Content-Type: application/json" \
  -d '{"validatorId": "0xaaa...", "amount": "5000000000"}'
```

Response contains Move call parameters:
```json
{
  "target": "0xpkg::ika_system::request_add_stake",
  "arguments": ["0xsystem", "0xaaa...", "5000000000"],
  "typeArguments": []
}
```

## 3. Sign and submit (TypeScript)

```typescript
import { Transaction } from '@mysten/sui/transactions'
import { SuiClient } from '@mysten/sui/client'

const client = new SuiClient({ url: 'https://fullnode.mainnet.sui.io' })

for (const alloc of allocations) {
  const params = await fetch('/api/v1/ika/agent/tx/stake', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({ validatorId: alloc.validatorId, amount: alloc.amount }),
  }).then(r => r.json())

  const tx = new Transaction()
  tx.moveCall({
    target: params.target,
    arguments: params.arguments.map(a => tx.pure(a)),
    typeArguments: params.typeArguments,
  })

  const result = await client.signAndExecuteTransaction({
    transaction: tx,
    signer: keypair,
  })
  console.log(`Staked ${alloc.amount} with ${alloc.validatorId}: ${result.digest}`)
}
```

## 4. Verify positions

After staking, check the delegators endpoint to confirm:

```bash
curl https://backend.inkwell.finance/api/v1/ika/agent/delegators/0xaaa... \
  -H "X-API-Key: lev_your_key"
```
