from __future__ import annotations

from dataclasses import asdict
import os
import threading
import time
from typing import Callable, Dict, List

from keysmith.addressing import AddressResult, create_address_result, generate_private_key_hex
from keysmith.estimates import (
    cumulative_chance,
    effective_pattern,
    estimate_probability,
    expected_attempts,
    expected_seconds,
)
from keysmith.validation import SearchConfig, address_fixed_prefix, matches_address


AddressGenerator = Callable[[SearchConfig], AddressResult]


class SearchSession:
    def __init__(self, generator: AddressGenerator | None = None):
        self._generator = generator or self._generate_once
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []
        self._status = "idle"
        self._config: SearchConfig | None = None
        self._attempts = 0
        self._started_at: float | None = None
        self._ended_at: float | None = None
        self._result: AddressResult | None = None
        self._error: str | None = None

    def start(self, config: SearchConfig) -> Dict[str, object]:
        self.stop(wait=True)
        with self._lock:
            self._stop_event = threading.Event()
            self._threads = []
            self._status = "running"
            self._config = config
            self._attempts = 0
            self._started_at = time.monotonic()
            self._ended_at = None
            self._result = None
            self._error = None

        for index in range(safe_worker_count(config.workers)):
            thread = threading.Thread(target=self._worker, name=f"keysmith-worker-{index + 1}", daemon=True)
            self._threads.append(thread)
            thread.start()
        return self.snapshot()

    def stop(self, wait: bool = False) -> Dict[str, object]:
        with self._lock:
            if self._status == "running":
                self._status = "stopping"
            self._stop_event.set()
            threads = list(self._threads)
        if wait:
            for thread in threads:
                thread.join(timeout=1)
            self._mark_stopped_if_needed()
        return self.snapshot()

    def snapshot(self) -> Dict[str, object]:
        self._mark_stopped_if_needed()
        with self._lock:
            now = time.monotonic()
            end = self._ended_at or now
            elapsed = 0.0 if self._started_at is None else max(0.0, end - self._started_at)
            rate = self._attempts / elapsed if elapsed > 0 else 0.0
            config = self._config
            estimate = estimate_probability(config).to_dict() if config else {}
            expected = expected_attempts(estimate["probability"]) if estimate else None
            result = asdict(self._result) if self._result else None
            chance = cumulative_chance(estimate["probability"], self._attempts) if estimate else 0.0
            return {
                "status": self._status,
                "attempts": self._attempts,
                "attempts_per_second": rate,
                "elapsed_seconds": elapsed,
                "expected_attempts": expected,
                "expected_seconds": expected_seconds(expected, rate) if expected is not None else None,
                "cumulative_chance": chance,
                "estimate": estimate,
                "config": asdict(config) if config else None,
                "result": result,
                "error": self._error,
                "process_steps": process_steps(),
                "format_breakdown": format_breakdown(config) if config else {},
            }

    def _worker(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                config = self._config
            if config is None:
                return
            try:
                result = self._generator(config)
            except StopIteration:
                self._stop_event.set()
                self._finish("stopped")
                return
            except Exception as exc:  # pragma: no cover - defensive runtime path
                with self._lock:
                    self._error = str(exc)
                self._stop_event.set()
                self._finish("error")
                return

            found = matches_address(result.address, config)
            with self._lock:
                self._attempts += 1
                if found and self._status == "running":
                    self._result = result
                    self._status = "found"
                    self._ended_at = time.monotonic()
                    self._stop_event.set()
                    return

    @staticmethod
    def _generate_once(config: SearchConfig) -> AddressResult:
        return create_address_result(generate_private_key_hex(), config.network, config.address_type)

    def _finish(self, status: str) -> None:
        with self._lock:
            if self._status not in {"found", "error"}:
                self._status = status
                self._ended_at = time.monotonic()

    def _mark_stopped_if_needed(self) -> None:
        with self._lock:
            if self._status != "stopping":
                return
            threads = list(self._threads)
        if all(not thread.is_alive() for thread in threads):
            self._finish("stopped")


def safe_worker_count(requested: int) -> int:
    cpu_count = os.cpu_count() or 1
    return max(1, min(requested, cpu_count, 8))


def process_steps() -> List[str]:
    return [
        "Generating a random private key with operating-system randomness.",
        "Deriving the secp256k1 public key locally.",
        "Encoding the selected Bitcoin address format.",
        "Checking the address against the vanity rule.",
    ]


def format_breakdown(config: SearchConfig) -> Dict[str, str]:
    fixed_prefix = address_fixed_prefix(config.network, config.address_type)
    return {
        "network": config.network,
        "address_type": config.address_type,
        "fixed_prefix": fixed_prefix,
        "searchable_pattern": effective_pattern(config),
        "match_mode": config.match_mode,
        "explanation": "The fixed prefix comes from the network and address type; the remaining pattern drives the search difficulty.",
    }
