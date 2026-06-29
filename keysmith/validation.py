from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from keysmith.addressing import BASE58_ALPHABET, BECH32_ALPHABET


NETWORKS = ("mainnet", "testnet")
TARGETS = ("bitcoin", "nostr")
ADDRESS_TYPES = ("p2pkh", "p2wpkh", "p2tr", "npub")
BITCOIN_ADDRESS_TYPES = ("p2pkh", "p2wpkh", "p2tr")
NOSTR_ADDRESS_TYPES = ("npub",)
MATCH_MODES = ("prefix", "suffix", "contains", "prefix_suffix")

BASE58_GUIDE = {
    "name": "Base58",
    "alphabet": BASE58_ALPHABET,
    "guide": "Base58 uses digits and letters except 0, O, I, and l.",
}
BECH32_GUIDE = {
    "name": "Bech32",
    "alphabet": BECH32_ALPHABET,
    "guide": "Bech32 uses lowercase characters: " + BECH32_ALPHABET,
}


@dataclass(frozen=True)
class SearchConfig:
    network: str
    address_type: str
    match_mode: str
    pattern: str
    case_sensitive: bool
    workers: int
    target: str = "bitcoin"
    suffix_pattern: str = ""


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    message: str
    normalized_pattern: str
    invalid_characters: List[Dict[str, object]]
    invalid_suffix_characters: List[Dict[str, object]]
    alphabet: str
    guide: str
    fixed_prefix: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "valid": self.valid,
            "message": self.message,
            "normalized_pattern": self.normalized_pattern,
            "invalid_characters": self.invalid_characters,
            "invalid_suffix_characters": self.invalid_suffix_characters,
            "alphabet": self.alphabet,
            "guide": self.guide,
            "fixed_prefix": self.fixed_prefix,
        }


def validate_pattern(config: SearchConfig) -> ValidationResult:
    _validate_config_shape(config)
    fixed_prefix = address_fixed_prefix(config.network, config.address_type)
    guide = alphabet_guide(config.address_type)
    normalized = normalize_pattern(config)
    normalized_suffix = normalize_suffix_pattern(config)
    validation_pattern = normalized if uses_bech32_alphabet(config.address_type) else config.pattern
    validation_suffix = normalized_suffix if uses_bech32_alphabet(config.address_type) else config.suffix_pattern
    prefix_conflict = (
        config.match_mode in {"prefix", "prefix_suffix"}
        and normalized
        and not _prefix_is_compatible(normalized, fixed_prefix, config)
    )
    invalid = [] if prefix_conflict else _invalid_for_config(validation_pattern, guide["alphabet"], config)
    invalid_suffix = invalid_characters(validation_suffix, guide["alphabet"])

    message = "Pattern is valid."
    valid = True
    if config.match_mode == "prefix_suffix" and (not normalized or not normalized_suffix):
        valid = False
        message = "Enter both a prefix and suffix to search for."
    elif not normalized:
        valid = False
        message = "Enter at least one character to search for."
    elif prefix_conflict:
        valid = False
        message = f"Prefix '{config.pattern}' conflicts with {config.network} {config.address_type.upper()} addresses, which start with '{fixed_prefix}'."
    elif invalid or invalid_suffix:
        valid = False
        names = ", ".join(item["char"] for item in invalid + invalid_suffix)
        message = f"Invalid character(s) for {guide['name']}: {names}."

    return ValidationResult(
        valid=valid,
        message=message,
        normalized_pattern=normalized,
        invalid_characters=invalid,
        invalid_suffix_characters=invalid_suffix,
        alphabet=guide["alphabet"],
        guide=guide["guide"],
        fixed_prefix=fixed_prefix,
    )


def _validate_config_shape(config: SearchConfig) -> None:
    if config.target not in TARGETS:
        raise ValueError(f"Unsupported target: {config.target}")
    if config.target == "bitcoin" and config.network not in NETWORKS:
        raise ValueError(f"Unsupported Bitcoin network: {config.network}")
    if config.target == "nostr" and config.network != "nostr":
        raise ValueError(f"Unsupported Nostr network: {config.network}")
    if config.target == "bitcoin" and config.address_type not in BITCOIN_ADDRESS_TYPES:
        raise ValueError(f"Unsupported Bitcoin address type: {config.address_type}")
    if config.target == "nostr" and config.address_type not in NOSTR_ADDRESS_TYPES:
        raise ValueError(f"Unsupported Nostr key type: {config.address_type}")
    if config.address_type not in ADDRESS_TYPES:
        raise ValueError(f"Unsupported address type: {config.address_type}")
    if config.match_mode not in MATCH_MODES:
        raise ValueError(f"Unsupported match mode: {config.match_mode}")
    if config.workers < 1:
        raise ValueError("Worker count must be at least 1")


def alphabet_guide(address_type: str) -> Dict[str, str]:
    if address_type == "p2pkh":
        return BASE58_GUIDE
    return BECH32_GUIDE


def normalize_pattern(config: SearchConfig) -> str:
    if uses_bech32_alphabet(config.address_type):
        return config.pattern.lower()
    if config.case_sensitive:
        return config.pattern
    return config.pattern.lower()


def normalize_suffix_pattern(config: SearchConfig) -> str:
    if uses_bech32_alphabet(config.address_type):
        return config.suffix_pattern.lower()
    if config.case_sensitive:
        return config.suffix_pattern
    return config.suffix_pattern.lower()


def invalid_characters(pattern: str, alphabet: str) -> List[Dict[str, object]]:
    allowed = set(alphabet)
    return [
        {"char": char, "index": index}
        for index, char in enumerate(pattern)
        if char not in allowed
    ]


def _invalid_for_config(pattern: str, alphabet: str, config: SearchConfig) -> List[Dict[str, object]]:
    if config.match_mode == "prefix" and uses_bech32_alphabet(config.address_type):
        for fixed_prefix in _possible_fixed_prefixes(config.network, config.address_type):
            if pattern.startswith(fixed_prefix):
                offset = len(fixed_prefix)
                return [
                    {"char": item["char"], "index": item["index"] + offset}
                    for item in invalid_characters(pattern[offset:], alphabet)
                ]
            if fixed_prefix.startswith(pattern):
                return []
    return invalid_characters(pattern, alphabet)


def address_fixed_prefix(network: str, address_type: str) -> str:
    if address_type == "npub":
        return "npub1"
    if address_type == "p2pkh":
        return "1" if network == "mainnet" else "m/n"
    if address_type == "p2wpkh":
        return "bc1q" if network == "mainnet" else "tb1q"
    if address_type == "p2tr":
        return "bc1p" if network == "mainnet" else "tb1p"
    raise ValueError(f"Unsupported address type: {address_type}")


def matches_address(address: str, config: SearchConfig) -> bool:
    pattern = normalize_pattern(config)
    suffix = normalize_suffix_pattern(config)
    candidate = address if config.case_sensitive and config.address_type == "p2pkh" else address.lower()
    if config.match_mode == "prefix":
        return candidate.startswith(pattern)
    if config.match_mode == "suffix":
        return candidate.endswith(pattern)
    if config.match_mode == "prefix_suffix":
        return candidate.startswith(pattern) and candidate.endswith(suffix)
    return pattern in candidate


def _prefix_is_compatible(pattern: str, fixed_prefix: str, config: SearchConfig) -> bool:
    possible_prefixes = _possible_fixed_prefixes(config.network, config.address_type)
    return any(_prefixes_can_overlap(pattern, possible) for possible in possible_prefixes)


def _possible_fixed_prefixes(network: str, address_type: str) -> List[str]:
    if address_type == "p2pkh" and network == "testnet":
        return ["m", "n"]
    return [address_fixed_prefix(network, address_type)]


def uses_bech32_alphabet(address_type: str) -> bool:
    return address_type in {"p2wpkh", "p2tr", "npub"}


def _prefixes_can_overlap(pattern: str, fixed_prefix: str) -> bool:
    overlap = min(len(pattern), len(fixed_prefix))
    return pattern[:overlap] == fixed_prefix[:overlap]
