from keysmith.addressing import AddressResult, create_address_result, private_key_hex_from_int
from keysmith.app import create_app
from keysmith.search import SearchSession


def fake_result(address: str) -> AddressResult:
    return AddressResult(
        address=address,
        network="mainnet",
        address_type="p2pkh",
        private_key_hex="01".rjust(64, "0"),
        wif="KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9uKrNrNFG6LHY2K",
        public_key_hex="02" + "00" * 32,
    )


def client_with_fake_search(address="1hit"):
    session = SearchSession(generator=lambda config: fake_result(address))
    app = create_app(session=session)
    return app.test_client()


def test_options_returns_supported_controls_and_guides():
    client = client_with_fake_search()

    response = client.get("/api/options")

    assert response.status_code == 200
    data = response.get_json()
    assert data["networks"] == ["mainnet", "testnet"]
    assert "p2tr" in data["address_types"]
    assert data["match_modes"] == ["prefix", "suffix", "contains"]
    assert data["targets"] == ["bitcoin", "nostr"]
    assert "Base58" in data["guides"]["p2pkh"]["name"]
    assert data["guides"]["npub"]["name"] == "Bech32"


def test_validate_returns_invalid_character_positions():
    client = client_with_fake_search()

    response = client.post(
        "/api/validate",
        json={
            "network": "mainnet",
            "address_type": "p2pkh",
            "match_mode": "prefix",
            "pattern": "10",
            "case_sensitive": True,
            "workers": 1,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert not data["valid"]
    assert data["invalid_characters"] == [{"char": "0", "index": 1}]


def test_start_rejects_invalid_input():
    client = client_with_fake_search()

    response = client.post(
        "/api/start",
        json={
            "network": "mainnet",
            "address_type": "p2wpkh",
            "match_mode": "prefix",
            "pattern": "bc1pbad",
            "case_sensitive": False,
            "workers": 1,
        },
    )

    assert response.status_code == 400
    assert "conflicts" in response.get_json()["message"]


def test_start_status_and_stop_search():
    client = client_with_fake_search("1hit")

    start = client.post(
        "/api/start",
        json={
            "network": "mainnet",
            "address_type": "p2pkh",
            "match_mode": "prefix",
            "pattern": "1hit",
            "case_sensitive": True,
            "workers": 1,
        },
    )
    status = client.get("/api/status")
    stop = client.post("/api/stop")

    assert start.status_code == 200
    assert status.status_code == 200
    assert stop.status_code == 200
    assert status.get_json()["status"] in {"running", "found", "stopped"}


def test_start_accepts_nostr_public_key_search():
    client = client_with_fake_search("npub1ace")

    response = client.post(
        "/api/start",
        json={
            "target": "nostr",
            "network": "nostr",
            "address_type": "npub",
            "match_mode": "prefix",
            "pattern": "npub1ace",
            "case_sensitive": False,
            "workers": 1,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["config"]["target"] == "nostr"


def test_index_serves_keysmith_ui():
    client = client_with_fake_search()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Keysmith" in response.data


def test_verify_secret_derives_bitcoin_address():
    client = client_with_fake_search()
    known = create_address_result(private_key_hex_from_int(1), "mainnet", "p2wpkh")

    response = client.post(
        "/api/verify-secret",
        json={
            "secret": known.wif,
            "target": "bitcoin",
            "network": "mainnet",
            "address_type": "p2wpkh",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["address"] == known.address


def test_verify_secret_rejects_invalid_secret():
    client = client_with_fake_search()

    response = client.post(
        "/api/verify-secret",
        json={
            "secret": "not-a-secret",
            "target": "nostr",
            "network": "nostr",
            "address_type": "npub",
        },
    )

    assert response.status_code == 400
    assert "Could not verify" in response.get_json()["message"]
