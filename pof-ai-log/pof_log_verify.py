#!/usr/bin/env python3
"""
pof_log_verify.py — Offline Merkle inclusion proof verifier.

Usage:
    python pof_log_verify.py --cert cert.json --log-url https://pof-ai-log-xxx.run.app

Fetches the inclusion proof from the log service and verifies it offline
using the same SHA-256 Merkle algorithm — no server trust required.
"""

import argparse
import hashlib
import json
import sys
import urllib.request


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_hash(data: bytes) -> bytes:
    return sha256(b"\x00" + data)


def node_hash(left: bytes, right: bytes) -> bytes:
    return sha256(b"\x01" + left + right)


def verify_proof(leaf_data: bytes, index: int, proof_hashes: list[str], expected_root: str) -> bool:
    computed = leaf_hash(leaf_data)
    i = index
    for sibling_hex in proof_hashes:
        sibling = bytes.fromhex(sibling_hex)
        if i % 2 == 1:
            computed = node_hash(sibling, computed)
        else:
            computed = node_hash(computed, sibling)
        i //= 2
    return computed.hex() == expected_root


def main():
    parser = argparse.ArgumentParser(description="Offline PoF-AI Merkle proof verifier")
    parser.add_argument("--cert", required=True, help="Path to FairnessCertificate JSON file")
    parser.add_argument("--log-url", required=True, help="Base URL of pof-ai-log service")
    args = parser.parse_args()

    with open(args.cert, "r") as f:
        cert = json.load(f)

    cert_id = cert.get("certificate_id")
    if not cert_id:
        print("ERROR: certificate_id not found in cert file")
        sys.exit(1)

    print(f"Certificate ID : {cert_id}")
    url = f"{args.log_url.rstrip('/')}/verify/{cert_id}"
    print(f"Fetching proof : {url}")

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        print(f"ERROR: Could not reach log service: {e}")
        sys.exit(1)

    proof = result.get("inclusion_proof", {})
    proof_hashes = proof.get("proof_hashes", [])
    expected_root = proof.get("merkle_root", "")
    index = proof.get("leaf_index", 0)

    leaf_data = json.dumps(cert, sort_keys=True, separators=(",", ":")).encode()
    ok = verify_proof(leaf_data, index, proof_hashes, expected_root)

    print(f"\nLeaf index     : {index}")
    print(f"Tree size      : {proof.get('tree_size', '?')}")
    print(f"Merkle root    : {expected_root[:24]}...")
    print(f"Proof steps    : {len(proof_hashes)}")
    print(f"\n{'✅ VALID — certificate is in the log and untampered' if ok else '❌ INVALID — proof verification failed'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
