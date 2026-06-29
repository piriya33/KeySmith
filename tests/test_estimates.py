from pytest import approx

from keysmith.estimates import (
    cumulative_chance,
    estimate_probability,
    expected_attempts,
    expected_seconds,
)
from keysmith.validation import SearchConfig


def test_bech32_prefix_estimate_subtracts_fixed_prefix():
    config = SearchConfig("mainnet", "p2wpkh", "prefix", "bc1qabc", False, 1)

    estimate = estimate_probability(config)

    assert estimate.effective_pattern == "abc"
    assert estimate.effective_length == 3
    assert estimate.probability == approx(1 / 32**3)


def test_base58_suffix_probability_uses_full_suffix_length():
    config = SearchConfig("mainnet", "p2pkh", "suffix", "Ab", True, 1)

    estimate = estimate_probability(config)

    assert estimate.effective_length == 2
    assert estimate.probability == approx(1 / 58**2)


def test_prefix_suffix_estimate_combines_searchable_ends():
    config = SearchConfig(
        "mainnet",
        "p2wpkh",
        "prefix_suffix",
        "bc1qabc",
        False,
        1,
        suffix_pattern="xyz",
    )

    estimate = estimate_probability(config)

    assert estimate.effective_pattern == "abcxyz"
    assert estimate.effective_length == 6
    assert estimate.probability == approx(1 / 32**6)


def test_contains_estimate_is_easier_than_prefix_for_same_pattern():
    prefix = SearchConfig("mainnet", "p2pkh", "prefix", "Ab", True, 1)
    contains = SearchConfig("mainnet", "p2pkh", "contains", "Ab", True, 1)

    assert estimate_probability(contains).probability > estimate_probability(prefix).probability


def test_cumulative_chance_increases_with_attempts():
    chance_10 = cumulative_chance(0.01, 10)
    chance_20 = cumulative_chance(0.01, 20)

    assert chance_20 > chance_10 > 0


def test_expected_seconds_uses_current_rate_and_handles_zero_speed():
    assert expected_attempts(0.25) == approx(4)
    assert expected_seconds(100, 25) == approx(4)
    assert expected_seconds(100, 0) is None


def test_nostr_prefix_estimate_subtracts_npub_fixed_prefix():
    config = SearchConfig("nostr", "npub", "prefix", "npub1ace", False, 1, target="nostr")

    estimate = estimate_probability(config)

    assert estimate.effective_pattern == "ace"
    assert estimate.effective_length == 3
    assert estimate.probability == approx(1 / 32**3)
