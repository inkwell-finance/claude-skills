---
name: sol-faucet
description: Claim SOL devnet/testnet airdrop from faucet.solana.com using browser automation. Uses persistent profile for GitHub auth. Designed to be looped every 8 hours. Usage - `/sol-faucet` (uses configured address) or `/sol-faucet <address>` or `/sol-faucet <address> testnet`.
allowed-tools: Bash(agent-browser:*), Read, Write
---

# Solana Faucet Airdrop

Automates claiming SOL from faucet.solana.com via headed browser with persistent GitHub auth.

## Configuration

Settings are stored in `~/.sol-faucet/config.json`:

```json
{
  "address": "<solana-wallet-address>",
  "network": "devnet",
  "amount": "5"
}
```

### First-run setup

If `~/.sol-faucet/config.json` does not exist, ask the user:

> **First-time setup for /sol-faucet.**
> What Solana wallet address should airdrops go to?

Create the config file with their answer and defaults for network/amount. Then proceed.

### Argument overrides

User arguments override config: first arg = address, second arg = network (devnet/testnet).

## Procedure

### 0. Load config

Read `~/.sol-faucet/config.json`. If missing, run first-time setup (ask user for address, create file). Merge any CLI arguments over config values.

### 1. Open faucet

```bash
agent-browser --headed --profile ~/.sol-faucet-profile --session sol-faucet --args "--disable-blink-features=AutomationControlled" open "https://faucet.solana.com"
```

```bash
agent-browser --session sol-faucet wait --load networkidle
```

### 2. Snapshot and check GitHub status

```bash
agent-browser --session sol-faucet snapshot -i
```

Look for:
- **"Higher Airdrop Limit Unlocked!"** + **"Disconnect your GitHub"** → GitHub connected, proceed
- **"Connect your GitHub"** → Tell user:
  > **Please click "Connect your GitHub" in the browser window and complete the OAuth flow. This only needs to happen once — the profile will persist your session.**
  
  Then poll every 5s until you see "Disconnect your GitHub" in the snapshot.

### 3. Fill address

Find the `textbox "Wallet Address"` ref and fill it:

```bash
agent-browser --session sol-faucet fill @WALLET_REF "<address>"
```

### 4. Select amount

The amount dropdown defaults to nothing (button shows "Amount"). You MUST select an amount or the Confirm button stays disabled.

Click the Amount button to open the dropdown:
```bash
agent-browser --session sol-faucet click @AMOUNT_REF
```

Wait briefly, re-snapshot to find amount option refs:
```bash
agent-browser --session sol-faucet wait 500
agent-browser --session sol-faucet snapshot -i
```

Options appear as buttons: `"0.5"`, `"1"`, `"2.5"`, `"5"`. Click the button matching the configured amount:
```bash
agent-browser --session sol-faucet click @AMOUNT_OPTION_REF
```

### 5. Confirm airdrop

Re-snapshot to verify the Confirm button is enabled (no `[disabled]` tag):
```bash
agent-browser --session sol-faucet wait 500
agent-browser --session sol-faucet snapshot -i
```

Click Confirm:
```bash
agent-browser --session sol-faucet click @CONFIRM_REF
```

### 6. Check result

Wait for the response:
```bash
agent-browser --session sol-faucet wait 5000
agent-browser --session sol-faucet snapshot -i
```

Look in the Notifications region for:
- **Success**: Will show a success message or transaction signature
- **Rate limited**: `"You have exceeded the 2 airdrops limit in the past 8 hour(s)"` — report and close
- **Error**: Report the error text

### 7. Close

```bash
agent-browser --session sol-faucet close
```

Report the result to the user.

## Important Notes

- Always use `--headed` — needed for first-time GitHub OAuth
- Always use `--profile ~/.sol-faucet-profile` — persists GitHub session across runs
- Always use `--session sol-faucet` — session isolation
- Always use `--args "--disable-blink-features=AutomationControlled"` — prevents bot detection
- The faucet allows max 2 requests per 8 hours
- Re-snapshot after every click to get fresh refs
- The Amount dropdown MUST be opened and a value selected — the Confirm button stays disabled without it
