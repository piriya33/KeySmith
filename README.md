# Keysmith

Keysmith is a local educational vanity key and address generator. It runs on your computer, opens a browser UI on `localhost`, and generates keys locally for learning purposes.

Keysmith currently supports Bitcoin vanity addresses and Nostr `npub` public keys. It is not a production wallet or identity manager. Private keys are sensitive. Do not use keys from an educational tool to store meaningful funds or important identities.

## Keysmith Lite for classrooms

`Keysmith-Lite.html` is a separate, self-contained student edition. It needs no Python installation or local server: share the single file, then double-click it to open it in a current version of Chrome, Edge, Firefox, or Safari.

The Lite edition performs the search entirely in browser workers and makes no network requests. It includes Bitcoin mainnet/testnet P2PKH, P2WPKH, and P2TR addresses; Nostr `npub`; prefix, suffix, anywhere, and prefix + suffix matching; input guidance; probability estimates; and an immediate Stop control. Its pure JavaScript cryptography uses a fixed-base lookup table and batched point normalization for speed, but it is still intended only for classroom experiments.

## Setup

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run

macOS/Linux:

```bash
source .venv/bin/activate
python -m keysmith.app
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m keysmith.app
```

Then open the printed localhost URL in your browser.

On macOS, you can also double-click `run_keysmith.command`. The first run may ask Terminal for permission and install dependencies into `.venv`.

On Windows, you can double-click `run_keysmith.bat`. The first run creates `.venv`, installs dependencies, and starts Keysmith.

## Portable apps

Portable builds include Python and all cryptography dependencies. Students can unzip the download and run Keysmith without installing Python:

- Apple Silicon Mac: `Keysmith-macOS-Apple-Silicon.zip`
- Intel Mac: `Keysmith-macOS-Intel.zip`
- Windows x64: `Keysmith-Windows-x64.zip`

Open the app or executable and Keysmith will launch in the default browser on a private local address. Use the **Exit Keysmith** button when finished; it stops any search and closes the local process.

To produce all three downloads, open the repository's **Actions** page, choose **Build portable apps**, and run the workflow. Version tags beginning with `v` also trigger it. The macOS and Windows jobs build on their native operating systems because portable executables cannot be cross-compiled reliably.

Portable development builds are not notarized or code-signed with publisher certificates. macOS may require right-clicking the app and choosing **Open** the first time. Windows SmartScreen may require **More info** then **Run anyway**. Public releases should be signed and notarized before broad distribution.

To build for the current computer locally:

```bash
python -m pip install ".[dev,build]"
pyinstaller --noconfirm --clean packaging/Keysmith.spec
```

## Test

macOS/Linux:

```bash
source .venv/bin/activate
python -m pytest -v
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -v
```

## Privacy

Keysmith does not need blockchain lookups, telemetry, or a hosted service. Generation happens locally inside the backend process.

## Offline Backup Checks

Keysmith includes an offline checklist and a backup verifier. Paste a WIF or `nsec` while offline to derive the public Bitcoin address or Nostr `npub`, then compare it with the value you wrote down.

Deleting the app is not the same as wiping secrets. Browser memory, terminal scrollback, swap, printer queues, screenshots, and backups may still contain sensitive material.
