import time
import threading

from keysmith.addressing import AddressResult
from keysmith.search import SearchSession
from keysmith.validation import SearchConfig


def result(address: str) -> AddressResult:
    return AddressResult(
        address=address,
        network="mainnet",
        address_type="p2pkh",
        private_key_hex="01".rjust(64, "0"),
        wif="KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9uKrNrNFG6LHY2K",
        public_key_hex="02" + "00" * 32,
    )


def test_search_records_found_result_and_stops():
    outputs = iter([result("1miss"), result("1hit")])
    session = SearchSession(generator=lambda config: next(outputs))
    config = SearchConfig("mainnet", "p2pkh", "prefix", "1hit", True, 1)

    snapshot = session.start(config)
    for _ in range(20):
        snapshot = session.snapshot()
        if snapshot["status"] == "found":
            break
        time.sleep(0.01)

    assert snapshot["status"] == "found"
    assert snapshot["result"]["address"] == "1hit"
    assert snapshot["attempts"] == 2


def test_stop_moves_running_search_to_stopped():
    session = SearchSession(generator=lambda config: result("1miss"))
    config = SearchConfig("mainnet", "p2pkh", "prefix", "1hit", True, 1)

    session.start(config)
    session.stop()

    snapshot = session.snapshot()
    assert snapshot["status"] in {"stopping", "stopped"}


def test_starting_new_search_resets_counters():
    outputs = iter([result("1hit"), result("1hit")])
    session = SearchSession(generator=lambda config: next(outputs))

    session.start(SearchConfig("mainnet", "p2pkh", "prefix", "1hit", True, 1))
    for _ in range(20):
        if session.snapshot()["status"] == "found":
            break
        time.sleep(0.01)

    session.start(SearchConfig("mainnet", "p2pkh", "prefix", "1hit", True, 1))
    for _ in range(20):
        snapshot = session.snapshot()
        if snapshot["status"] == "found":
            break
        time.sleep(0.01)

    assert snapshot["attempts"] == 1


def test_snapshot_includes_educational_state_and_estimates():
    session = SearchSession(generator=lambda config: result("1miss"))
    config = SearchConfig("mainnet", "p2pkh", "prefix", "1abc", True, 1)

    snapshot = session.start(config)

    assert "probability" in snapshot["estimate"]
    assert "Generating a random private key" in snapshot["process_steps"][0]
    assert snapshot["format_breakdown"]["fixed_prefix"] == "1"
    assert snapshot["format_breakdown"]["searchable_pattern"] == "abc"
    session.stop()


def test_old_worker_cannot_mutate_new_search_after_restart():
    release_old = threading.Event()
    calls = 0

    def generator(config):
        nonlocal calls
        calls += 1
        if calls == 1:
            release_old.wait(timeout=2)
            return result("1old")
        return result("1new")

    session = SearchSession(generator=generator)
    session.start(SearchConfig("mainnet", "p2pkh", "prefix", "1old", True, 1))
    time.sleep(0.02)
    session.start(SearchConfig("mainnet", "p2pkh", "prefix", "1new", True, 1))
    release_old.set()

    for _ in range(30):
        snapshot = session.snapshot()
        if snapshot["status"] == "found":
            break
        time.sleep(0.01)

    assert snapshot["result"]["address"] == "1new"


def test_stop_prevents_attempt_count_after_in_flight_generation_finishes():
    release = threading.Event()

    def generator(config):
        release.wait(timeout=2)
        return result("1miss")

    session = SearchSession(generator=generator)
    session.start(SearchConfig("mainnet", "p2pkh", "prefix", "1hit", True, 1))
    time.sleep(0.02)
    session.stop()
    release.set()
    time.sleep(0.02)

    assert session.snapshot()["attempts"] == 0
