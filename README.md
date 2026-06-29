# Keysmith

Keysmith is a local educational vanity key and address generator. It runs on your Mac, opens a browser UI on `localhost`, and generates keys locally for learning purposes.

Keysmith currently supports Bitcoin vanity addresses and Nostr `npub` public keys. It is not a production wallet or identity manager. Private keys are sensitive. Do not use keys from an educational tool to store meaningful funds or important identities.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run

```bash
source .venv/bin/activate
python -m keysmith.app
```

Then open the printed localhost URL in your browser.

On macOS, you can also double-click `run_keysmith.command`. The first run may ask Terminal for permission and install dependencies into `.venv`.

## Test

```bash
source .venv/bin/activate
python -m pytest -v
```

## Privacy

Keysmith does not need blockchain lookups, telemetry, or a hosted service. Generation happens locally inside the backend process.

## Offline Backup Checks

Keysmith includes an offline checklist and a backup verifier. Paste a WIF or `nsec` while offline to derive the public Bitcoin address or Nostr `npub`, then compare it with the value you wrote down.

Deleting the app is not the same as wiping secrets. Browser memory, terminal scrollback, swap, printer queues, screenshots, and backups may still contain sensitive material.
