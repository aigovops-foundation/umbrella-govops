"""Ed25519 signing for evidence bundles and the receipts inside them.

Same primitives as AIGovOps Beacon, so one verifier reads both:

* Ed25519 signatures, keys as PEM (PKCS#8 private / SubjectPublicKeyInfo public)
* receipts canonicalised per RFC 8785 (JCS) with the ``signature`` block
  removed, signature block ``{alg, key_fpr, canonical_form, sig_b64}``
* ``key_fpr`` in the SSH-style wire form ``SHA256:<base64, no padding>``

The verifier never trusts a key that travels with the bundle: the public key
is always supplied by the person verifying.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

ALG = "Ed25519"
CANONICAL_FORM = "RFC8785"


class SigningError(ValueError):
    """A key could not be loaded or a signature could not be produced."""


def canonicalize(obj: Any) -> bytes:
    """RFC 8785 canonical bytes for the JSON this tool emits.

    Umbrella receipts contain only strings, integers, booleans, null, arrays
    and objects with ASCII keys; for that subset, sorted-key compact JSON with
    UTF-8 output is byte-identical to JCS. Floats are refused rather than
    risk a divergent number encoding.
    """
    def _no_floats(v: Any) -> None:
        if isinstance(v, float):
            raise SigningError("floats are not permitted in signed receipts")
        if isinstance(v, dict):
            for x in v.values():
                _no_floats(x)
        elif isinstance(v, list):
            for x in v:
                _no_floats(x)

    _no_floats(obj)
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _raw_public(pub: Ed25519PublicKey) -> bytes:
    return pub.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )


def key_fpr(pub: Ed25519PublicKey) -> str:
    digest = hashlib.sha256(_raw_public(pub)).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def generate_keypair(out_dir: Path, name: str = "signing") -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    priv_path = out_dir / f"{name}.pem"
    pub_path = out_dir / f"{name}.pub.pem"
    if priv_path.exists():
        raise SigningError(f"{priv_path} already exists; refusing to overwrite a key")
    key = Ed25519PrivateKey.generate()
    priv_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    priv_path.chmod(0o600)
    pub_path.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return priv_path, pub_path


def load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (ValueError, TypeError, OSError) as exc:
        raise SigningError(f"{path}: cannot load private key — {exc}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise SigningError(f"{path}: not an Ed25519 private key")
    return key


def load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (ValueError, TypeError, OSError) as exc:
        raise SigningError(f"{path}: cannot load public key — {exc}") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise SigningError(f"{path}: not an Ed25519 public key")
    return key


def signature_block(key: Ed25519PrivateKey, message: bytes) -> dict[str, str]:
    return {
        "alg": ALG,
        "key_fpr": key_fpr(key.public_key()),
        "canonical_form": CANONICAL_FORM,
        "sig_b64": base64.b64encode(key.sign(message)).decode(),
    }


def sign_receipt(key: Ed25519PrivateKey, receipt: dict) -> dict:
    body = {k: v for k, v in receipt.items() if k != "signature"}
    return {**body, "signature": signature_block(key, canonicalize(body))}


def verify_bytes(pub: Ed25519PublicKey, message: bytes, block: dict) -> bool:
    if not isinstance(block, dict) or block.get("alg") != ALG:
        return False
    try:
        pub.verify(base64.b64decode(block.get("sig_b64", ""), validate=True), message)
    except (InvalidSignature, ValueError):
        return False
    return True


def verify_receipt(pub: Ed25519PublicKey, receipt: dict) -> bool:
    body = {k: v for k, v in receipt.items() if k != "signature"}
    try:
        message = canonicalize(body)
    except SigningError:
        return False
    return verify_bytes(pub, message, receipt.get("signature") or {})
