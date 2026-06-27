from keysmith.addressing import (
    create_address_result,
    create_nostr_result,
    nostr_npub_from_hex,
    private_key_hex_from_int,
)


def test_p2pkh_mainnet_known_private_key_one():
    result = create_address_result(private_key_hex_from_int(1), "mainnet", "p2pkh")

    assert result.address == "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"
    assert result.wif.startswith(("K", "L"))
    assert result.private_key_hex == "0" * 63 + "1"
    assert result.public_key_hex.startswith("02")


def test_p2pkh_testnet_uses_testnet_prefixes():
    result = create_address_result(private_key_hex_from_int(1), "testnet", "p2pkh")

    assert result.address[0] in {"m", "n"}
    assert result.wif.startswith("c")


def test_p2wpkh_addresses_use_bech32_prefixes():
    mainnet = create_address_result(private_key_hex_from_int(1), "mainnet", "p2wpkh")
    testnet = create_address_result(private_key_hex_from_int(1), "testnet", "p2wpkh")

    assert mainnet.address == "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    assert testnet.address == "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"
    assert mainnet.public_key_hex.startswith("02")


def test_p2tr_addresses_use_bech32m_prefixes_and_x_only_key():
    mainnet = create_address_result(private_key_hex_from_int(1), "mainnet", "p2tr")
    testnet = create_address_result(private_key_hex_from_int(1), "testnet", "p2tr")

    assert mainnet.address == "bc1pmfr3p9j00pfxjh0zmgp99y8zftmd3s5pmedqhyptwy6lm87hf5sspknck9"
    assert testnet.address == "tb1pmfr3p9j00pfxjh0zmgp99y8zftmd3s5pmedqhyptwy6lm87hf5ssk79hv2"
    assert len(mainnet.x_only_public_key_hex) == 64
    assert mainnet.public_key_hex.startswith("02")


def test_nostr_npub_matches_nip19_vector():
    public_key_hex = "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d"

    assert (
        nostr_npub_from_hex(public_key_hex)
        == "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    )


def test_nostr_result_exports_npub_nsec_and_x_only_public_key():
    result = create_nostr_result(private_key_hex_from_int(1))

    assert result.address.startswith("npub1")
    assert result.nsec.startswith("nsec1")
    assert result.network == "nostr"
    assert result.address_type == "npub"
    assert len(result.x_only_public_key_hex) == 64
    assert result.private_key_export_label == "nsec private key"
