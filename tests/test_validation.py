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


def test_fixed_prefixes_match_network_and_address_type():
    assert address_fixed_prefix("mainnet", "p2pkh") == "1"
    assert address_fixed_prefix("testnet", "p2wpkh") == "tb1q"
    assert address_fixed_prefix("mainnet", "p2tr") == "bc1p"
