from __future__ import annotations

import base64
import io
import webbrowser

from flask import Flask, jsonify, request, send_from_directory
import qrcode
from qrcode.image.svg import SvgPathImage

from keysmith.addressing import derive_from_secret
from keysmith.search import SearchSession
from keysmith.validation import (
    BASE58_GUIDE,
    BECH32_GUIDE,
    BITCOIN_ADDRESS_TYPES,
    MATCH_MODES,
    NETWORKS,
    NOSTR_ADDRESS_TYPES,
    SearchConfig,
    TARGETS,
    validate_pattern,
)


def create_app(session: SearchSession | None = None) -> Flask:
    app = Flask(__name__, static_folder="static")
    search_session = session or SearchSession()

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/options")
    def options():
        return jsonify(
            {
                "networks": list(NETWORKS),
                "targets": list(TARGETS),
                "address_types": list(BITCOIN_ADDRESS_TYPES),
                "nostr_address_types": list(NOSTR_ADDRESS_TYPES),
                "match_modes": list(MATCH_MODES),
                "guides": {
                    "p2pkh": BASE58_GUIDE,
                    "p2wpkh": BECH32_GUIDE,
                    "p2tr": BECH32_GUIDE,
                    "npub": BECH32_GUIDE,
                },
            }
        )

    @app.post("/api/validate")
    def validate():
        config = parse_config(request.get_json(silent=True) or {})
        return jsonify(validate_pattern(config).to_dict())

    @app.post("/api/start")
    def start():
        config = parse_config(request.get_json(silent=True) or {})
        validation = validate_pattern(config)
        if not validation.valid:
            return jsonify(validation.to_dict()), 400
        return jsonify(with_paper_qr_codes(search_session.start(config)))

    @app.post("/api/stop")
    def stop():
        return jsonify(search_session.stop())

    @app.get("/api/status")
    def status():
        return jsonify(with_paper_qr_codes(search_session.snapshot()))

    @app.post("/api/verify-secret")
    def verify_secret():
        payload = request.get_json(silent=True) or {}
        try:
            result = derive_from_secret(
                str(payload.get("secret", "")),
                str(payload.get("target", "bitcoin")),
                str(payload.get("network", "mainnet")),
                str(payload.get("address_type", "p2pkh")),
            )
        except Exception:
            return jsonify({"valid": False, "message": "Could not verify that secret for the selected format."}), 400
        return jsonify({"valid": True, **result_to_public_dict(result)})

    return app


def parse_config(payload: dict) -> SearchConfig:
    target = str(payload.get("target", "bitcoin"))
    return SearchConfig(
        network=str(payload.get("network", "nostr" if target == "nostr" else "mainnet")),
        address_type=str(payload.get("address_type", "npub" if target == "nostr" else "p2pkh")),
        match_mode=str(payload.get("match_mode", "prefix")),
        pattern=str(payload.get("pattern", "")),
        case_sensitive=bool(payload.get("case_sensitive", False)),
        workers=int(payload.get("workers", 1)),
        target=target,
    )


def result_to_public_dict(result) -> dict:
    return {
        "address": result.address,
        "network": result.network,
        "address_type": result.address_type,
        "public_key_hex": result.public_key_hex,
        "x_only_public_key_hex": result.x_only_public_key_hex,
    }


def with_paper_qr_codes(snapshot: dict) -> dict:
    result = snapshot.get("result")
    if not result:
        return snapshot

    private_export = result.get("nsec") or result.get("wif")
    if not private_export:
        return snapshot

    result["paper_qr_codes"] = {
        "public": qr_svg_data_uri(result["address"]),
        "private": qr_svg_data_uri(private_export),
    }
    return snapshot


def qr_svg_data_uri(value: str) -> str:
    image = qrcode.make(
        value,
        image_factory=SvgPathImage,
        box_size=8,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    buffer = io.BytesIO()
    image.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def main() -> None:
    app = create_app()
    host = "127.0.0.1"
    port = 5000
    url = f"http://{host}:{port}"
    print(f"Keysmith running at {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
