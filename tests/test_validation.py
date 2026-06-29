from keysmith.validation import (
    BECH32_GUIDE,
    SearchConfig,
    address_fixed_prefix,
    matches_address,
    validate_pattern,
)


def test_base58_validation_reports_illegal_character_positions():
    config = SearchConfig("mainnet", "p2pkh", "prefix", "10OlI", True, 1)

    result = validate_pattern(config)

    assert not result.valid
    assert [(item["char"], item["index"]) for item in result.invalid_characters] == [
        ("0", 1),
        ("O", 2),
        ("l", 3),
        ("I", 4),
    ]
    assert "except 0, O, I, and l" in result.guide


def test_base58_case_insensitive_validation_keeps_original_alphabet_rules():
    valid_upper = SearchConfig("mainnet", "p2pkh", "contains", "L", False, 1)
    invalid_upper = SearchConfig("mainnet", "p2pkh", "contains", "O", False, 1)

    assert validate_pattern(valid_upper).valid
    invalid = validate_pattern(invalid_upper)
    assert not invalid.valid
    assert invalid.invalid_characters == [{"char": "O", "index": 0}]


def test_bech32_validation_normalizes_pattern_and_reports_bad_chars():
    config = SearchConfig("mainnet", "p2wpkh", "contains", "QZ!", False, 1)

    result = validate_pattern(config)

    assert result.normalized_pattern == "qz!"
    assert not result.valid
    assert result.invalid_characters == [{"char": "!", "index": 2}]
    assert result.alphabet == BECH32_GUIDE["alphabet"]


def test_prefix_conflicts_are_rejected_before_search():
    wrong_taproot = SearchConfig("mainnet", "p2tr", "prefix", "bc1qabc", False, 1)
    wrong_testnet = SearchConfig("testnet", "p2pkh", "prefix", "1abc", True, 1)

    assert not validate_pattern(wrong_taproot).valid
    assert "conflicts" in validate_pattern(wrong_taproot).message
    assert not validate_pattern(wrong_testnet).valid


def test_matching_modes_respect_case_rules():
    base58 = SearchConfig("mainnet", "p2pkh", "prefix", "1Bg", True, 1)
    bech32 = SearchConfig("mainnet", "p2wpkh", "contains", "QABC", False, 1)

    assert matches_address("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH", base58)
    assert not matches_address("1bggZ9tcN4rm9KBzDn7KprQz87SZ26SAMH", base58)
    assert matches_address("bc1qabcxyz", bech32)


def test_suffix_and_contains_matching():
    suffix = SearchConfig("mainnet", "p2pkh", "suffix", "SAMH", True, 1)
    contains = SearchConfig("mainnet", "p2pkh", "contains", "Kpr", True, 1)

    assert matches_address("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH", suffix)
    assert matches_address("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH", contains)


def test_prefix_suffix_matching_requires_both_ends():
    config = SearchConfig(
        "mainnet",
        "p2pkh",
        "prefix_suffix",
        "1Bg",
        True,
        1,
        suffix_pattern="SAMH",
    )

    assert matches_address("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH", config)
    assert not matches_address("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26XXXX", config)
    assert not matches_address("1XxGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH", config)


def test_prefix_suffix_validation_reports_suffix_invalid_characters():
    config = SearchConfig(
        "mainnet",
        "p2wpkh",
        "prefix_suffix",
        "bc1qabc",
        False,
        1,
        suffix_pattern="xyz!",
    )

    result = validate_pattern(config)

    assert not result.valid
    assert result.invalid_suffix_characters == [{"char": "!", "index": 3}]


def test_prefix_suffix_validation_ignores_bech32_fixed_prefix_characters():
    config = SearchConfig(
        "mainnet",
        "p2wpkh",
        "prefix_suffix",
        "bc1qqxz",
        False,
        1,
        suffix_pattern="xyz",
    )

    result = validate_pattern(config)

    assert result.valid
    assert result.invalid_characters == []


def test_fixed_prefixes_match_network_and_address_type():
    assert address_fixed_prefix("mainnet", "p2pkh") == "1"
    assert address_fixed_prefix("testnet", "p2wpkh") == "tb1q"
    assert address_fixed_prefix("mainnet", "p2tr") == "bc1p"


def test_nostr_prefix_validation_accounts_for_npub_fixed_prefix():
    valid = SearchConfig("nostr", "npub", "prefix", "npub1ace", False, 1, target="nostr")
    conflict = SearchConfig("nostr", "npub", "prefix", "nsec1ace", False, 1, target="nostr")

    result = validate_pattern(valid)

    assert result.valid
    assert result.fixed_prefix == "npub1"
    assert not validate_pattern(conflict).valid
