from keysmith.addressing import create_address_result, private_key_hex_from_int


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
