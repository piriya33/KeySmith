from __future__ import annotations

from dataclasses import dataclass
import math

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

    if effective_length == 0:
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
        note="Educational estimate; actual search time varies with randomness and machine speed.",
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
