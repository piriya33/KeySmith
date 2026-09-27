from __future__ import annotations

from dataclasses import dataclass
import math

from keysmith.addressing import BASE58_ALPHABET
from keysmith.validation import SearchConfig, address_fixed_prefix, alphabet_guide, normalize_pattern, normalize_suffix_pattern


APPROX_ADDRESS_LENGTHS = {
    "p2pkh": 34,
    "p2wpkh": 42,
    "p2tr": 62,
    "npub": 63,
}


@dataclass(frozen=True)
class ProbabilityEstimate:
    probability: float
    alphabet_size: int
    effective_pattern: str
    effective_length: int
    mode: str
    note: str

    def to_dict(self) -> dict:
        return {
            "probability": self.probability,
            "alphabet_size": self.alphabet_size,
            "effective_pattern": self.effective_pattern,
            "effective_length": self.effective_length,
            "mode": self.mode,
            "note": self.note,
        }


def estimate_probability(config: SearchConfig) -> ProbabilityEstimate:
    alphabet_size = len(alphabet_guide(config.address_type)["alphabet"])
    effective = effective_pattern(config)
    effective_length = len(effective)

    note = "Educational estimate; actual search time varies with randomness and machine speed."
    legacy_probability = _p2pkh_search_probability(config)

    if legacy_probability is not None:
        probability = legacy_probability
        note = "Legacy Base58 prefixes are position-dependent; this estimate accounts for address-length bias."
    elif effective_length == 0:
        probability = 1.0
    elif config.match_mode == "contains":
        positions = max(1, APPROX_ADDRESS_LENGTHS[config.address_type] - effective_length + 1)
        exact = 1 / alphabet_size**effective_length
        probability = min(1.0, positions * exact)
    else:
        probability = 1 / alphabet_size**effective_length

    return ProbabilityEstimate(
        probability=probability,
        alphabet_size=alphabet_size,
        effective_pattern=effective,
        effective_length=effective_length,
        mode=config.match_mode,
        note=note,
    )


def effective_pattern(config: SearchConfig) -> str:
    pattern = normalize_pattern(config)
    if config.match_mode == "prefix_suffix":
        return _effective_prefix_pattern(config, pattern) + normalize_suffix_pattern(config)
    if config.match_mode != "prefix":
        return pattern

    return _effective_prefix_pattern(config, pattern)


def _effective_prefix_pattern(config: SearchConfig, pattern: str) -> str:
    if config.match_mode not in {"prefix", "prefix_suffix"}:
        return pattern

    prefixes = [address_fixed_prefix(config.network, config.address_type)]
    if config.target == "bitcoin" and config.address_type == "p2pkh" and config.network == "testnet":
        prefixes = ["m", "n"]

    for fixed_prefix in prefixes:
        if pattern.startswith(fixed_prefix):
            return pattern[len(fixed_prefix) :]
        if fixed_prefix.startswith(pattern):
            return ""
    return pattern


def _p2pkh_search_probability(config: SearchConfig) -> float | None:
    if config.address_type != "p2pkh" or config.match_mode not in {"prefix", "prefix_suffix"}:
        return None

    pattern = normalize_pattern(config)
    variants = [pattern] if config.case_sensitive else _case_variants(pattern)
    if variants is None:
        return None

    prefix_probability = sum(_p2pkh_prefix_probability(value, config.network) for value in variants)
    if prefix_probability <= 0:
        return 0.0
    if config.match_mode == "prefix_suffix":
        prefix_probability *= _base58_loose_probability(normalize_suffix_pattern(config), config.case_sensitive)
    return prefix_probability


def _p2pkh_prefix_probability(pattern: str, network: str) -> float:
    if network == "testnet":
        low = 0x6F << 192
        high = (0x70 << 192) - 1
        return _base58_prefix_interval_probability(pattern, low, high, 1 << 192)

    if not pattern.startswith("1"):
        return 0.0
    remainder = pattern[1:]
    extra_zero_bytes = len(remainder) - len(remainder.lstrip("1"))
    if extra_zero_bytes == len(remainder):
        return 256.0**-extra_zero_bytes
    if extra_zero_bytes >= 20:
        return 0.0

    prefix = remainder[extra_zero_bytes:]
    high_bits = 8 * (24 - extra_zero_bytes)
    low_bits = high_bits - 8
    return _base58_prefix_interval_probability(
        prefix,
        1 << low_bits,
        (1 << high_bits) - 1,
        1 << 192,
    )


def _base58_prefix_interval_probability(prefix: str, low: int, high: int, domain_size: int) -> float:
    if not prefix or BASE58_ALPHABET.find(prefix[0]) <= 0:
        return 0.0

    value = 0
    for char in prefix:
        digit = BASE58_ALPHABET.find(char)
        if digit < 0:
            return 0.0
        value = value * 58 + digit

    count = 0
    for length in range(len(prefix), 41):
        scale = 58 ** (length - len(prefix))
        interval_low = value * scale
        interval_high = (value + 1) * scale - 1
        overlap_low = max(interval_low, low)
        overlap_high = min(interval_high, high)
        if overlap_high >= overlap_low:
            count += overlap_high - overlap_low + 1
    return count / domain_size


def _case_variants(value: str) -> list[str] | None:
    variants = [""]
    for char in value:
        swapped = char.swapcase()
        choices = [char, swapped] if swapped != char and swapped in BASE58_ALPHABET else [char]
        if len(variants) * len(choices) > 4096:
            return None
        variants = [prefix + choice for prefix in variants for choice in choices]
    return variants


def _base58_loose_probability(value: str, case_sensitive: bool) -> float:
    probability = 1.0
    for char in value:
        swapped = char.swapcase()
        choices = 2 if not case_sensitive and swapped != char and swapped in BASE58_ALPHABET else 1
        probability *= choices / 58
    return probability


def expected_attempts(probability: float) -> float:
    if probability <= 0:
        return math.inf
    return 1 / probability


def expected_seconds(attempts: float, attempts_per_second: float) -> float | None:
    if attempts_per_second <= 0:
        return None
    return attempts / attempts_per_second


def cumulative_chance(probability: float, attempts: int) -> float:
    if probability <= 0 or attempts <= 0:
        return 0.0
    if probability >= 1:
        return 1.0
    return 1 - math.pow(1 - probability, attempts)
