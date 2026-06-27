# Keysmith Design

## Goal

Build Keysmith, a local educational Bitcoin vanity address generator that runs on a Mac M1, exposes a simple browser GUI, and supports Bitcoin mainnet and testnet address generation for P2PKH, P2WPKH, and P2TR.

The app must generate keys locally, show probabilistic search estimates, and provide a kill switch that stops active generation promptly.

Keysmith should be named and structured so it can later expand beyond Bitcoin addresses into other key and identity formats, such as Nostr public keys.

## Non-Goals

- Hosted web service or remote key generation.
- Production wallet management.
- Balance lookup, blockchain queries, or network broadcasting.
- GPU mining or highly optimized native vanity generation.
- Multi-coin support.

## User Experience

The app starts as a local service and opens in a browser at a localhost URL. The first screen is the usable generator, not a landing page.

Controls:

- Network: mainnet or testnet.
- Address type: P2PKH, P2WPKH, or P2TR.
- Match mode: prefix, suffix, or contains.
- Pattern text.
- Case sensitivity where applicable.
- Worker count, defaulting to a conservative value based on available CPU cores.
- Start button.
- Stop kill switch.

The UI should prioritize education. It should expose the search process in plain language and show useful intermediate state when possible, without overwhelming the user or leaking unnecessary private key material while the search is running.

Live display:

- Current status: idle, running, stopped, or found.
- Attempts.
- Attempts per second.
- Elapsed time.
- Estimated probability per attempt.
- Expected attempts.
- Expected time at the current observed rate.
- Live probability of having found a match by now.
- A short "what is happening now" explanation, such as generating a private key, deriving a public key, encoding the selected address type, and checking the vanity rule.
- The selected address format breakdown, including the fixed network/type prefix and the variable portion being searched.
- A compact explanation of why longer patterns are exponentially harder.

Result display:

- Matching address.
- Network and address type.
- Private key export in WIF.
- Raw private key hex.
- Public key or x-only public key for Taproot.
- Attempts and elapsed time.
- Copy buttons for individual fields.

The result panel must present a clear educational warning before exposing private key material.

## Architecture

Use a local browser app backed by a local Python service.

Stack:

- Backend: Python with Flask.
- Frontend: simple HTML, CSS, and JavaScript served by the backend.
- Worker: Python thread or process pool controlled by a stop event.
- Crypto/address module: isolated Python module for key generation, address derivation, matching, and estimate helpers.

The backend owns all private key generation. The browser sends only configuration such as network, address type, pattern, match mode, case sensitivity, and worker count.

Progress should be exposed through a polling endpoint. The browser should poll this endpoint while a search is active. This keeps the first version simple and reliable.

## Address Generation

For each attempt:

1. Generate a random secp256k1 private key with secure OS randomness.
2. Derive the public key.
3. Encode the selected address type for the selected network.
4. Check the address against the active match rule.
5. Update attempt counters and progress estimates.
6. Stop all workers when a match is found or when the kill switch is pressed.

Supported address families:

- P2PKH:
  - mainnet addresses beginning with `1`.
  - testnet addresses typically beginning with `m` or `n`.
- P2WPKH:
  - mainnet Bech32 addresses beginning with `bc1q`.
  - testnet Bech32 addresses beginning with `tb1q`.
- P2TR:
  - mainnet Bech32m addresses beginning with `bc1p`.
  - testnet Bech32m addresses beginning with `tb1p`.

Use established Bitcoin/address libraries when possible instead of hand-rolling cryptographic primitives. Keep address encoding logic covered by tests.

## Matching Rules

The app supports three match modes:

- Prefix: address must start with the requested pattern.
- Suffix: address must end with the requested pattern.
- Contains: address must contain the requested pattern anywhere.

Prefix matching should account for fixed address prefixes. For example, a P2WPKH mainnet address always starts with `bc1q`, so searching for `bc1qabc` should estimate only the variable `abc` portion as difficult. Searching for a prefix that conflicts with the selected network or address type should be rejected before generation starts.

Case sensitivity:

- P2PKH uses Base58 characters and can support case-sensitive matching.
- Bech32 and Bech32m addresses are displayed lowercase in this app. Bech32-family matching should normalize the pattern to lowercase and treat matching as case-insensitive.

Invalid characters should be rejected before generation starts based on the selected address family. The pattern input should validate live and highlight individual illegal characters.

Input guidance:

- P2PKH uses the Base58 alphabet: digits and letters except `0`, `O`, `I`, and `l`.
- P2WPKH and P2TR use the Bech32 character set: `qpzry9x8gf2tvdw0s3jn54khce6mua7l`.
- The UI should show the relevant alphabet near the input.
- Illegal characters should be visibly marked in the pattern text or mirrored validation preview.
- The validation message should name each invalid character and briefly explain why it is invalid for the selected address family.
- When the user changes network or address type, validation should rerun immediately and update the guide.

## Probability Estimates

The GUI should show educational estimates, not guarantees.

For each configuration, compute an approximate probability per attempt using the relevant address alphabet and effective pattern length:

- P2PKH uses Base58-style estimates.
- P2WPKH and P2TR use Bech32-style estimates.
- Prefix estimates subtract fixed network/address prefixes when the user's pattern includes them.
- Suffix estimates use the full suffix pattern length.
- Contains estimates approximate the chance that the pattern appears in any valid sliding position of the address.

Display:

- Probability per attempt.
- Expected attempts, approximately `1 / probability`.
- Expected time based on current attempts per second.
- Live cumulative chance, approximately `1 - (1 - probability) ^ attempts`.

The UI must label estimates as probabilistic and update expected time as observed speed changes.

## Stop Behavior

The Stop button is the kill switch.

When pressed:

- The backend sets a shared stop signal.
- Workers check the stop signal frequently.
- Progress switches to stopped after active workers exit.
- No new attempts are started after stop is requested.
- A later Start begins a fresh search with fresh counters.

If a result is found and Stop is pressed at nearly the same time, the found result wins if it was recorded first; otherwise the search ends as stopped.

## Safety and Privacy

- The app runs locally and should not send generated keys or addresses to remote services.
- No telemetry.
- No blockchain lookups.
- No automatic file export.
- Private key fields should be clearly labeled as sensitive.
- The app should be described as educational, not as a secure wallet.
- Dependencies should be standard, inspectable, and documented.

## Error Handling

Validate inputs before starting:

- Non-empty pattern.
- Pattern characters valid for the selected address family.
- Prefix pattern compatible with the selected network and address type.
- Worker count within a safe local range.

Show clear inline errors in the GUI and do not start generation when validation fails.

Runtime errors should stop the active search and surface a concise error message without exposing stack traces in the browser.

## Testing

Automated tests should cover:

- P2PKH mainnet/testnet address generation.
- P2WPKH mainnet/testnet address generation.
- P2TR mainnet/testnet address generation.
- Prefix, suffix, and contains matching.
- Invalid pattern rejection.
- Prefix compatibility validation.
- Probability estimate sanity checks.
- Worker stop behavior.

Manual verification should cover:

- Starting a search from the browser.
- Stopping a search from the browser.
- Finding an easy short pattern.
- Copying result fields.
- Running on Mac M1 with the documented setup command.

## Initial Implementation Scope

The first version should prioritize correctness, clarity, and local safety over raw speed. A simple local browser GUI, tested crypto/address module, live progress, and reliable stop behavior are sufficient for the initial release.
