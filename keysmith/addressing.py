from __future__ import annotations

from dataclasses import dataclass
import hashlib
import secrets
from typing import Iterable, List

from coincurve import PublicKey


SECP256K1_ORDER = int(
    "fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141",
    16,
)
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BECH32_ALPHABET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


@dataclass(frozen=True)
class CandidateResult:
    address: str
    private_key_hex: str


@dataclass(frozen=True)
class AddressResult:
    address: str
    network: str
    address_type: str
    private_key_hex: str
    wif: str
    public_key_hex: str
    x_only_public_key_hex: str | None = None
    nsec: str | None = None
    private_key_export_label: str = "WIF private key"


def private_key_hex_from_int(value: int) -> str:
    if not 1 <= value < SECP256K1_ORDER:
        raise ValueError("Private key integer is outside secp256k1 range")
    return value.to_bytes(32, "big").hex()


def generate_private_key_hex() -> str:
    value = secrets.randbelow(SECP256K1_ORDER - 1) + 1
    return private_key_hex_from_int(value)


def create_address_result(private_key_hex: str, network: str, address_type: str) -> AddressResult:
    private_key = bytes.fromhex(private_key_hex)
    if len(private_key) != 32:
        raise ValueError("Private key must be 32 bytes")

    public_key = PublicKey.from_valid_secret(private_key)
    public_key_bytes = public_key.format(compressed=True)
    wif = encode_wif(private_key, network)

    if address_type == "p2pkh":
        address = p2pkh_address(public_key_bytes, network)
        x_only = None
    elif address_type == "p2wpkh":
        address = p2wpkh_address(public_key_bytes, network)
        x_only = None
    elif address_type == "p2tr":
        x_only_bytes = taproot_output_key(private_key)
        address = p2tr_address(x_only_bytes, network)
        x_only = x_only_bytes.hex()
    else:
        raise ValueError(f"Unsupported address type: {address_type}")

    return AddressResult(
        address=address,
        network=network,
        address_type=address_type,
        private_key_hex=private_key_hex,
        wif=wif,
        public_key_hex=public_key_bytes.hex(),
        x_only_public_key_hex=x_only,
    )


def create_candidate_result(private_key_hex: str, network: str, address_type: str, target: str) -> CandidateResult:
    if target == "nostr":
        return create_nostr_candidate_result(private_key_hex)
    private_key = bytes.fromhex(private_key_hex)
    if len(private_key) != 32:
        raise ValueError("Private key must be 32 bytes")

    public_key = PublicKey.from_valid_secret(private_key)
    public_key_bytes = public_key.format(compressed=True)
    if address_type == "p2pkh":
        address = p2pkh_address(public_key_bytes, network)
    elif address_type == "p2wpkh":
        address = p2wpkh_address(public_key_bytes, network)
    elif address_type == "p2tr":
        address = p2tr_address(taproot_output_key(private_key), network)
    else:
        raise ValueError(f"Unsupported address type: {address_type}")
    return CandidateResult(address=address, private_key_hex=private_key_hex)


def finalize_candidate_result(
    candidate: CandidateResult,
    network: str,
    address_type: str,
    target: str,
) -> AddressResult:
    if target == "nostr":
        result = create_nostr_result(candidate.private_key_hex)
    else:
        result = create_address_result(candidate.private_key_hex, network, address_type)
    if result.address != candidate.address:
        raise ValueError("Finalized result does not match candidate address")
    return result


def create_nostr_result(private_key_hex: str) -> AddressResult:
    private_key = bytes.fromhex(private_key_hex)
    if len(private_key) != 32:
        raise ValueError("Private key must be 32 bytes")

    public_key = PublicKey.from_valid_secret(private_key)
    public_key_bytes = public_key.format(compressed=True)
    x_only_public_key = public_key.format(compressed=False)[1:33]
    npub = nostr_npub_from_hex(x_only_public_key.hex())
    nsec = nostr_nsec_from_hex(private_key_hex)
    return AddressResult(
        address=npub,
        network="nostr",
        address_type="npub",
        private_key_hex=private_key_hex,
        wif="",
        public_key_hex=public_key_bytes.hex(),
        x_only_public_key_hex=x_only_public_key.hex(),
        nsec=nsec,
        private_key_export_label="nsec private key",
    )


def create_nostr_candidate_result(private_key_hex: str) -> CandidateResult:
    private_key = bytes.fromhex(private_key_hex)
    if len(private_key) != 32:
        raise ValueError("Private key must be 32 bytes")

    public_key = PublicKey.from_valid_secret(private_key)
    x_only_public_key = public_key.format(compressed=False)[1:33]
    return CandidateResult(
        address=nostr_npub_from_hex(x_only_public_key.hex()),
        private_key_hex=private_key_hex,
    )


def hash160(data: bytes) -> bytes:
    sha = hashlib.sha256(data).digest()
    ripe = hashlib.new("ripemd160")
    ripe.update(sha)
    return ripe.digest()


def base58check_encode(version: bytes, payload: bytes) -> str:
    data = version + payload
    checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    return base58_encode(data + checksum)


def base58check_decode(value: str) -> bytes:
    data = base58_decode(value)
    if len(data) < 5:
        raise ValueError("Base58Check value is too short")
    payload, checksum = data[:-4], data[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if checksum != expected:
        raise ValueError("Base58Check checksum mismatch")
    return payload


def base58_encode(data: bytes) -> str:
    number = int.from_bytes(data, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded

    leading_zeroes = len(data) - len(data.lstrip(b"\x00"))
    return "1" * leading_zeroes + (encoded or "")


def base58_decode(value: str) -> bytes:
    number = 0
    for char in value:
        if char not in BASE58_ALPHABET:
            raise ValueError(f"Invalid Base58 character: {char}")
        number = number * 58 + BASE58_ALPHABET.index(char)
    decoded = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    leading_zeroes = len(value) - len(value.lstrip("1"))
    return b"\x00" * leading_zeroes + decoded


def encode_wif(private_key: bytes, network: str) -> str:
    version = b"\x80" if network == "mainnet" else b"\xef"
    return base58check_encode(version, private_key + b"\x01")


def p2pkh_address(public_key_bytes: bytes, network: str) -> str:
    version = b"\x00" if network == "mainnet" else b"\x6f"
    return base58check_encode(version, hash160(public_key_bytes))


def p2wpkh_address(public_key_bytes: bytes, network: str) -> str:
    hrp = "bc" if network == "mainnet" else "tb"
    return encode_segwit_address(hrp, 0, hash160(public_key_bytes), "bech32")


def p2tr_address(x_only_public_key: bytes, network: str) -> str:
    hrp = "bc" if network == "mainnet" else "tb"
    return encode_segwit_address(hrp, 1, x_only_public_key, "bech32m")


def nostr_npub_from_hex(public_key_hex: str) -> str:
    return nostr_bech32_from_hex("npub", public_key_hex)


def nostr_nsec_from_hex(private_key_hex: str) -> str:
    return nostr_bech32_from_hex("nsec", private_key_hex)


def nostr_bech32_from_hex(hrp: str, value_hex: str) -> str:
    data = bytes.fromhex(value_hex)
    if len(data) != 32:
        raise ValueError("Nostr bare keys must be 32 bytes")
    return bech32_encode(hrp, convert_bits(data, 8, 5, True), "bech32")


def derive_from_secret(secret: str, target: str, network: str, address_type: str) -> AddressResult:
    normalized = secret.strip()
    if is_private_key_hex(normalized):
        private_key_hex = normalized.lower()
        if target == "nostr":
            return create_nostr_result(private_key_hex)
        return create_address_result(private_key_hex, network, address_type)
    if target == "nostr":
        private_key_hex = private_key_hex_from_nsec(normalized)
        return create_nostr_result(private_key_hex)
    private_key_hex = private_key_hex_from_wif(normalized, network)
    return create_address_result(private_key_hex, network, address_type)


def is_private_key_hex(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        key_int = int(value, 16)
    except ValueError:
        return False
    return 1 <= key_int < SECP256K1_ORDER


def private_key_hex_from_wif(wif: str, network: str) -> str:
    data = base58check_decode(wif)
    expected_version = b"\x80" if network == "mainnet" else b"\xef"
    if not data.startswith(expected_version):
        raise ValueError("WIF network byte does not match selected network")
    payload = data[1:]
    if len(payload) == 33 and payload[-1] == 1:
        payload = payload[:-1]
    if len(payload) != 32:
        raise ValueError("WIF does not contain a 32-byte private key")
    return payload.hex()


def private_key_hex_from_nsec(nsec: str) -> str:
    hrp, data = bech32_decode(nsec)
    if hrp != "nsec":
        raise ValueError("Nostr private key must start with nsec")
    decoded = bytes(convert_bits_values(data, 5, 8, False))
    if len(decoded) != 32:
        raise ValueError("nsec does not contain a 32-byte private key")
    return decoded.hex()


def taproot_output_key(private_key: bytes) -> bytes:
    secret_int = int.from_bytes(private_key, "big")
    internal_secret = _secret_with_even_y(secret_int)
    internal_public_key = PublicKey.from_valid_secret(internal_secret.to_bytes(32, "big"))
    internal_x = internal_public_key.format(compressed=False)[1:33]
    tweak = int.from_bytes(tagged_hash("TapTweak", internal_x), "big") % SECP256K1_ORDER
    if tweak == 0:
        output_key = internal_public_key
    else:
        tweak_key = PublicKey.from_valid_secret(tweak.to_bytes(32, "big"))
        output_key = PublicKey.combine_keys([internal_public_key, tweak_key])
    return output_key.format(compressed=False)[1:33]


def _secret_with_even_y(secret_int: int) -> int:
    public_key = PublicKey.from_valid_secret(secret_int.to_bytes(32, "big"))
    compressed = public_key.format(compressed=True)
    if compressed[0] == 2:
        return secret_int
    return SECP256K1_ORDER - secret_int


def tagged_hash(tag: str, data: bytes) -> bytes:
    tag_hash = hashlib.sha256(tag.encode("ascii")).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()


def encode_segwit_address(hrp: str, witness_version: int, witness_program: bytes, spec: str) -> str:
    data = [witness_version] + convert_bits(witness_program, 8, 5, True)
    return bech32_encode(hrp, data, spec)


def bech32_encode(hrp: str, data: List[int], spec: str) -> str:
    combined = data + bech32_create_checksum(hrp, data, spec)
    return hrp + "1" + "".join(BECH32_ALPHABET[value] for value in combined)


def bech32_decode(value: str) -> tuple[str, List[int]]:
    if value.lower() != value and value.upper() != value:
        raise ValueError("Bech32 cannot mix uppercase and lowercase")
    value = value.lower()
    separator = value.rfind("1")
    if separator < 1 or separator + 7 > len(value):
        raise ValueError("Invalid Bech32 separator")
    hrp = value[:separator]
    data = [BECH32_ALPHABET.find(char) for char in value[separator + 1 :]]
    if any(part < 0 for part in data):
        raise ValueError("Invalid Bech32 character")
    if bech32_polymod(bech32_hrp_expand(hrp) + data) != 1:
        raise ValueError("Bech32 checksum mismatch")
    return hrp, data[:-6]


def bech32_create_checksum(hrp: str, data: List[int], spec: str) -> List[int]:
    constant = 1 if spec == "bech32" else 0x2BC830A3
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ constant
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def bech32_hrp_expand(hrp: str) -> List[int]:
    return [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]


def bech32_polymod(values: Iterable[int]) -> int:
    generators = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = (checksum & 0x1FFFFFF) << 5 ^ value
        for index, generator in enumerate(generators):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def convert_bits(data: bytes, from_bits: int, to_bits: int, pad: bool) -> List[int]:
    return convert_bits_values(data, from_bits, to_bits, pad)


def convert_bits_values(data: Iterable[int], from_bits: int, to_bits: int, pad: bool) -> List[int]:
    accumulator = 0
    bits = 0
    result = []
    max_value = (1 << to_bits) - 1
    for value in data:
        if value < 0 or value >> from_bits:
            raise ValueError("Invalid bit group")
        accumulator = (accumulator << from_bits) | value
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            result.append((accumulator >> bits) & max_value)
    if pad and bits:
        result.append((accumulator << (to_bits - bits)) & max_value)
    elif bits >= from_bits or ((accumulator << (to_bits - bits)) & max_value):
        raise ValueError("Invalid padding")
    return result
