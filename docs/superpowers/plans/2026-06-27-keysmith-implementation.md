# Keysmith Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Keysmith as a local educational browser app for generating Bitcoin vanity addresses on Mac M1.

**Architecture:** A Flask backend serves a static browser UI and exposes JSON endpoints for validation, starting/stopping searches, and polling status. Core Bitcoin behavior lives in focused Python modules for address generation, matching/validation, probabilistic estimates, and worker session state.

**Tech Stack:** Python 3.9+, Flask, coincurve for secp256k1 operations, pytest, vanilla HTML/CSS/JavaScript.

---

## File Structure

- `pyproject.toml`: package metadata, runtime dependencies, pytest configuration.
- `README.md`: setup, run, safety notes, educational scope.
- `keysmith/__init__.py`: package marker and version.
- `keysmith/addressing.py`: secure key generation, Base58Check, Bech32/Bech32m, P2PKH/P2WPKH/P2TR address derivation, WIF export.
- `keysmith/validation.py`: pattern validation, alphabet guidance, prefix compatibility, match helpers.
- `keysmith/estimates.py`: probability-per-attempt and time/chance helpers.
- `keysmith/search.py`: thread-backed search session, stop signal, progress snapshots.
- `keysmith/app.py`: Flask app factory and JSON routes.
- `keysmith/static/index.html`: educational single-screen UI.
- `keysmith/static/styles.css`: UI styling.
- `keysmith/static/app.js`: form behavior, live validation, start/stop/polling, copy buttons.
- `tests/test_addressing.py`: Bitcoin address derivation and encoding tests.
- `tests/test_validation.py`: alphabets, invalid highlighting data, prefix compatibility, matching.
- `tests/test_estimates.py`: probability estimate sanity tests.
- `tests/test_search.py`: worker stop/found behavior with injectable generator.
- `tests/test_app.py`: Flask endpoint tests.

## Task 1: Project Skeleton and Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `keysmith/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_package.py`:

```python
from keysmith import __version__


def test_package_exposes_version():
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_package.py -v`

Expected: fail because `keysmith` is not importable.

- [ ] **Step 3: Add package skeleton**

Create `pyproject.toml` with Flask, coincurve, and pytest dependencies. Create `keysmith/__init__.py` with `__version__ = "0.1.0"`. Add a README with local-only educational safety notes and run commands.

- [ ] **Step 4: Install and verify**

Run: `python3 -m pip install -e ".[dev]"`

Run: `python3 -m pytest tests/test_package.py -v`

Expected: pass.

- [ ] **Step 5: Commit**

Run: `git add pyproject.toml README.md keysmith/__init__.py tests/test_package.py && git commit -m "chore: scaffold keysmith project"`

## Task 2: Bitcoin Addressing Core

**Files:**
- Create: `keysmith/addressing.py`
- Create: `tests/test_addressing.py`

- [ ] **Step 1: Write failing tests**

Tests must cover deterministic derivation from private key integer `1` for:

- P2PKH mainnet begins with `1` and testnet begins with `m` or `n`.
- P2WPKH mainnet begins with `bc1q` and testnet begins with `tb1q`.
- P2TR mainnet begins with `bc1p` and testnet begins with `tb1p`.
- WIF mainnet begins with `K` or `L`; WIF testnet begins with `c`.
- Generated result includes address, private key hex, WIF, compressed public key hex, and Taproot x-only pubkey for P2TR.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_addressing.py -v`

Expected: fail because `keysmith.addressing` does not exist.

- [ ] **Step 3: Implement addressing**

Implement secure private key generation with `secrets.randbelow`, secp256k1 public key derivation with `coincurve`, Base58Check, Bech32, Bech32m, HASH160, WIF export, and address creation for P2PKH, P2WPKH, and P2TR.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_addressing.py -v`

Expected: pass.

- [ ] **Step 5: Commit**

Run: `git add keysmith/addressing.py tests/test_addressing.py && git commit -m "feat: derive bitcoin address formats"`

## Task 3: Pattern Validation and Matching

**Files:**
- Create: `keysmith/validation.py`
- Create: `tests/test_validation.py`

- [ ] **Step 1: Write failing tests**

Tests must cover:

- Base58 rejects `0`, `O`, `I`, and `l`, returning character positions.
- Bech32 rejects characters outside `qpzry9x8gf2tvdw0s3jn54khce6mua7l`.
- Bech32 patterns normalize to lowercase.
- Prefix conflict is rejected for `bc1q` pattern with P2TR and `1abc` with testnet P2PKH.
- Prefix, suffix, and contains matching work.
- Alphabet guide data is returned for the selected address type.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validation.py -v`

Expected: fail because `keysmith.validation` does not exist.

- [ ] **Step 3: Implement validation**

Implement `SearchConfig`, `ValidationResult`, alphabet constants, `validate_pattern`, `matches_address`, and `address_fixed_prefix`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_validation.py -v`

Expected: pass.

- [ ] **Step 5: Commit**

Run: `git add keysmith/validation.py tests/test_validation.py && git commit -m "feat: validate vanity patterns"`

## Task 4: Probability Estimates

**Files:**
- Create: `keysmith/estimates.py`
- Create: `tests/test_estimates.py`

- [ ] **Step 1: Write failing tests**

Tests must cover:

- Prefix estimate for `bc1qabc` on mainnet P2WPKH uses effective length `3`.
- Base58 suffix length `2` has probability near `1 / 58**2`.
- Contains estimate is easier than exact prefix for the same length.
- Cumulative chance increases with attempts.
- Expected seconds uses current attempts per second and returns `None` when speed is zero.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_estimates.py -v`

Expected: fail because `keysmith.estimates` does not exist.

- [ ] **Step 3: Implement estimates**

Implement `estimate_probability`, `expected_attempts`, `expected_seconds`, and `cumulative_chance` using educational approximations from the spec.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_estimates.py -v`

Expected: pass.

- [ ] **Step 5: Commit**

Run: `git add keysmith/estimates.py tests/test_estimates.py && git commit -m "feat: estimate vanity search odds"`

## Task 5: Search Session and Stop Behavior

**Files:**
- Create: `keysmith/search.py`
- Create: `tests/test_search.py`

- [ ] **Step 1: Write failing tests**

Tests must cover:

- A search with an injectable generator records a found result and stops.
- `stop()` moves a running search to stopped and prevents new attempts.
- Starting a new search resets counters.
- Snapshot includes status, attempts, rate, elapsed time, estimates, educational step text, and format breakdown.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_search.py -v`

Expected: fail because `keysmith.search` does not exist.

- [ ] **Step 3: Implement search session**

Implement a thread-backed `SearchSession` with a lock-protected state object, stop event, worker count cap, injectable generator for tests, and progress snapshot serialization.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_search.py -v`

Expected: pass.

- [ ] **Step 5: Commit**

Run: `git add keysmith/search.py tests/test_search.py && git commit -m "feat: add stoppable vanity search"`

## Task 6: Flask API

**Files:**
- Create: `keysmith/app.py`
- Create: `tests/test_app.py`

- [ ] **Step 1: Write failing tests**

Tests must cover:

- `GET /api/options` returns networks, address types, match modes, and alphabet guide.
- `POST /api/validate` returns invalid character positions.
- `POST /api/start` rejects invalid input.
- `POST /api/start` starts valid search and returns snapshot.
- `POST /api/stop` stops the active search.
- `GET /api/status` returns current snapshot.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_app.py -v`

Expected: fail because `keysmith.app` does not exist.

- [ ] **Step 3: Implement Flask app**

Implement the app factory, routes, request parsing, validation errors, and a `python -m keysmith.app` entry point.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_app.py -v`

Expected: pass.

- [ ] **Step 5: Commit**

Run: `git add keysmith/app.py tests/test_app.py && git commit -m "feat: expose local keysmith api"`

## Task 7: Educational Browser UI

**Files:**
- Create: `keysmith/static/index.html`
- Create: `keysmith/static/styles.css`
- Create: `keysmith/static/app.js`
- Modify: `keysmith/app.py`

- [ ] **Step 1: Add endpoint test**

Extend `tests/test_app.py` with a test that `GET /` returns HTML containing `Keysmith`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_app.py::test_index_serves_keysmith_ui -v`

Expected: fail because the route or static file is missing.

- [ ] **Step 3: Implement UI**

Build a single-screen educational app with form controls, live character highlighting, alphabet guide, process panel, probability panel, start/stop controls, result warning, and copy buttons.

- [ ] **Step 4: Run app/API tests**

Run: `python3 -m pytest tests/test_app.py -v`

Expected: pass.

- [ ] **Step 5: Commit**

Run: `git add keysmith/app.py keysmith/static/index.html keysmith/static/styles.css keysmith/static/app.js tests/test_app.py && git commit -m "feat: add educational browser ui"`

## Task 8: Final Verification and Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run complete test suite**

Run: `python3 -m pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Run local app smoke test**

Run: `python3 -m keysmith.app`

Expected: Flask starts on a localhost port. Stop it after confirming startup.

- [ ] **Step 3: Update README if commands changed**

Ensure README documents install, run, test, local-only safety, and educational limitations.

- [ ] **Step 4: Commit final docs**

Run: `git add README.md && git commit -m "docs: explain running keysmith"` if README changed.

## Self-Review Notes

- Spec coverage: the plan covers local Flask/browser app, Bitcoin mainnet/testnet, P2PKH/P2WPKH/P2TR, prefix/suffix/contains, educational UI process display, live invalid-character guidance, probability estimates, stop behavior, and tests.
- Placeholder scan: no task relies on unresolved placeholders.
- Type consistency: shared config and snapshot concepts are introduced before API/UI integration.
