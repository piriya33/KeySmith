from __future__ import annotations

from dataclasses import asdict
import multiprocessing
import os
import queue
import threading
import time
from typing import Callable, Dict, List, Union

from keysmith.addressing import (
    AddressResult,
    CandidateResult,
    create_candidate_result,
    finalize_candidate_result,
    generate_private_key_hex,
)
from keysmith.estimates import (
    cumulative_chance,
    effective_pattern,
    estimate_probability,
    expected_attempts,
    expected_seconds,
)
from keysmith.validation import SearchConfig, address_fixed_prefix, matches_address


SearchResult = Union[AddressResult, CandidateResult]
AddressGenerator = Callable[[SearchConfig], SearchResult]
BATCH_SIZE = 100


class SearchSession:
    def __init__(self, generator: AddressGenerator | None = None):
        self._generator = generator
        self._worker_mode = "thread" if generator else "process"
        self._lock = threading.Lock()
        self._stop_event = self._new_stop_event()
        self._progress_queue = None
        self._threads: List[threading.Thread] = []
        self._status = "idle"
        self._config: SearchConfig | None = None
        self._attempts = 0
        self._started_at: float | None = None
        self._ended_at: float | None = None
        self._result: AddressResult | None = None
        self._error: str | None = None
        self._run_id = 0

    def start(self, config: SearchConfig) -> Dict[str, object]:
        self.stop(wait=True)
        with self._lock:
            self._run_id += 1
            run_id = self._run_id
            stop_event = self._new_stop_event()
            self._stop_event = stop_event
            self._progress_queue = self._new_progress_queue()
            self._threads = []
            self._status = "running"
            self._config = config
            self._attempts = 0
            self._started_at = time.monotonic()
            self._ended_at = None
            self._result = None
            self._error = None

        for index in range(safe_worker_count(config.workers)):
            worker = self._build_worker(index, run_id, config, stop_event, self._progress_queue)
            self._threads.append(worker)
            worker.start()
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
        self._drain_progress()
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
                "worker_mode": self._worker_mode,
                "process_steps": process_steps(config),
                "format_breakdown": format_breakdown(config) if config else {},
            }

    def _worker(self, run_id: int, config: SearchConfig, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            if stop_event.is_set():
                return
            try:
                result = self._generator(config)
            except StopIteration:
                stop_event.set()
                self._finish(run_id, "stopped")
                return
            except Exception as exc:  # pragma: no cover - defensive runtime path
                with self._lock:
                    if self._run_id == run_id:
                        self._error = str(exc)
                stop_event.set()
                self._finish(run_id, "error")
                return

            if stop_event.is_set():
                return
            found = matches_address(result.address, config)
            final_result = self._finalize_result(result, config) if found else None
            with self._lock:
                if self._run_id != run_id or self._stop_event is not stop_event or self._status != "running":
                    return
                self._attempts += 1
                if found:
                    self._result = final_result
                    self._status = "found"
                    self._ended_at = time.monotonic()
                    stop_event.set()
                    return

    def _build_worker(self, index, run_id, config, stop_event, progress_queue):
        if self._generator:
            return threading.Thread(
                target=self._worker,
                args=(run_id, config, stop_event),
                name=f"keysmith-worker-{index + 1}",
                daemon=True,
            )
        context = multiprocessing.get_context("spawn")
        return context.Process(
            target=_process_worker,
            args=(run_id, config, stop_event, progress_queue),
            name=f"keysmith-process-{index + 1}",
            daemon=True,
        )

    def _new_stop_event(self):
        if self._generator:
            return threading.Event()
        return multiprocessing.get_context("spawn").Event()

    def _new_progress_queue(self):
        if self._generator:
            return None
        return multiprocessing.get_context("spawn").Queue()

    def _drain_progress(self) -> None:
        progress_queue = self._progress_queue
        if progress_queue is None:
            return
        while True:
            try:
                message = progress_queue.get_nowait()
            except queue.Empty:
                return
            self._apply_process_message(message)

    def _apply_process_message(self, message: Dict[str, object]) -> None:
        run_id = message.get("run_id")
        with self._lock:
            if run_id != self._run_id:
                return
            if message["type"] == "attempts" and self._status == "running":
                self._attempts += int(message["count"])
            elif message["type"] == "found" and self._status == "running":
                self._attempts += int(message["attempts"])
                candidate = CandidateResult(
                    address=str(message["address"]),
                    private_key_hex=str(message["private_key_hex"]),
                )
                self._result = finalize_candidate_result(candidate, self._config.network, self._config.address_type, self._config.target)
                self._status = "found"
                self._ended_at = time.monotonic()
                self._stop_event.set()
            elif message["type"] == "error":
                self._error = str(message["error"])
                self._status = "error"
                self._ended_at = time.monotonic()
                self._stop_event.set()

    @staticmethod
    def _finalize_result(result: SearchResult, config: SearchConfig) -> AddressResult:
        if isinstance(result, AddressResult):
            return result
        return finalize_candidate_result(result, config.network, config.address_type, config.target)

    def _finish(self, run_id: int, status: str) -> None:
        with self._lock:
            if self._run_id != run_id:
                return
            if self._status not in {"found", "error"}:
                self._status = status
                self._ended_at = time.monotonic()

    def _mark_stopped_if_needed(self) -> None:
        with self._lock:
            if self._status != "stopping":
                return
            threads = list(self._threads)
        if all(not thread.is_alive() for thread in threads):
            self._finish(self._run_id, "stopped")


def safe_worker_count(requested: int) -> int:
    cpu_count = os.cpu_count() or 1
    return max(1, min(requested, cpu_count, 8))


def _process_worker(run_id: int, config: SearchConfig, stop_event, progress_queue) -> None:
    pending_attempts = 0
    try:
        while not stop_event.is_set():
            candidate = create_candidate_result(
                generate_private_key_hex(),
                config.network,
                config.address_type,
                config.target,
            )
            if stop_event.is_set():
                return
            pending_attempts += 1
            if matches_address(candidate.address, config):
                progress_queue.put(
                    {
                        "type": "found",
                        "run_id": run_id,
                        "attempts": pending_attempts,
                        "address": candidate.address,
                        "private_key_hex": candidate.private_key_hex,
                    }
                )
                stop_event.set()
                return
            if pending_attempts >= BATCH_SIZE:
                progress_queue.put({"type": "attempts", "run_id": run_id, "count": pending_attempts})
                pending_attempts = 0
        if pending_attempts:
            progress_queue.put({"type": "attempts", "run_id": run_id, "count": pending_attempts})
    except Exception as exc:  # pragma: no cover - subprocess defensive path
        progress_queue.put({"type": "error", "run_id": run_id, "error": str(exc)})
        stop_event.set()


def process_steps(config: SearchConfig | None = None) -> List[str]:
    if config and config.target == "nostr":
        return [
            "Generating a random private key with operating-system randomness.",
            "Deriving the secp256k1 x-only public key locally.",
            "Encoding the Nostr public key as an npub Bech32 string.",
            "Checking the npub against the vanity rule.",
        ]
    return [
        "Generating a random private key with operating-system randomness.",
        "Deriving the secp256k1 public key locally.",
        "Encoding the selected Bitcoin address format.",
        "Checking the address against the vanity rule.",
    ]


def format_breakdown(config: SearchConfig) -> Dict[str, str]:
    fixed_prefix = address_fixed_prefix(config.network, config.address_type)
    family = "Nostr public key" if config.target == "nostr" else "Bitcoin address"
    return {
        "target": config.target,
        "family": family,
        "network": config.network,
        "address_type": config.address_type,
        "fixed_prefix": fixed_prefix,
        "searchable_pattern": effective_pattern(config),
        "match_mode": config.match_mode,
        "explanation": "The fixed prefix comes from the selected format; the remaining pattern drives the search difficulty.",
    }
