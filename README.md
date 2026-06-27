# Keysmith

Keysmith is a local educational Bitcoin vanity address generator. It runs on your Mac, opens a browser UI on `localhost`, and generates keys locally for learning purposes.

Keysmith is not a production wallet. Private keys are sensitive. Do not use keys from an educational tool to store meaningful funds.

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

## Test

```bash
source .venv/bin/activate
python -m pytest -v
```

## Privacy

Keysmith does not need blockchain lookups, telemetry, or a hosted service. Generation happens locally inside the backend process.
