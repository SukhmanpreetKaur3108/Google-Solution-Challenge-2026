"""
RFC 6962-style Merkle Tree implementation (SHA-256).

Design rationale
----------------
We use a Merkle log rather than a blockchain for three reasons:
1. **Simplicity & speed**: No consensus protocol, no gas fees, no peer network.
   Appends are O(log n) and verify in milliseconds.
2. **Cryptographic equivalence**: A Merkle inclusion proof gives the same
   tamper-evidence guarantee as a blockchain Merkle root — any change to a
   leaf invalidates every proof generated after it.
3. **Auditability**: The design follows RFC 6962 (Certificate Transparency),
   which has been battle-tested since 2013 for TLS certificate logs.

References
----------
- Haber, S. & Stornetta, W.S. (1991). How to time-stamp a digital document.
  Journal of Cryptology, 3(2), 99–111. — Original tamper-evident log concept.
- Laurie, B., Langley, A., & Kasper, E. (2013). Certificate Transparency.
  RFC 6962. IETF. — Defines the Merkle log structure used here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _leaf_hash(data: bytes) -> bytes:
    """RFC 6962 §2.1: leaf hash = SHA-256(0x00 || data)."""
    return _sha256(b"\x00" + data)


def _node_hash(left: bytes, right: bytes) -> bytes:
    """RFC 6962 §2.1: node hash = SHA-256(0x01 || left || right)."""
    return _sha256(b"\x01" + left + right)


@dataclass
class MerkleTree:
    """
    An append-only Merkle log.

    Internal state:
    - leaves: raw data bytes for each leaf
    - _leaf_hashes: SHA-256 leaf hashes
    """
    leaves: list[bytes] = field(default_factory=list)
    _leaf_hashes: list[bytes] = field(default_factory=list, repr=False)

    def append(self, data: bytes) -> int:
        """Append a leaf. Returns the 0-based leaf index."""
        self.leaves.append(data)
        self._leaf_hashes.append(_leaf_hash(data))
        return len(self.leaves) - 1

    def root(self) -> Optional[bytes]:
        """Compute the current Merkle root."""
        if not self._leaf_hashes:
            return None
        return self._compute_root(self._leaf_hashes)

    def root_hex(self) -> str:
        r = self.root()
        return r.hex() if r else ""

    def inclusion_proof(self, index: int) -> list[bytes]:
        """
        Return the Merkle inclusion proof (list of sibling hashes) for leaf at `index`.
        Follows RFC 6962 §2.1.3 path format.
        """
        n = len(self._leaf_hashes)
        if index < 0 or index >= n:
            raise IndexError(f"Leaf index {index} out of range [0, {n})")
        return self._build_proof(self._leaf_hashes[:], index)

    def verify_inclusion(
        self,
        data: bytes,
        index: int,
        proof: list[bytes],
        expected_root: bytes,
    ) -> bool:
        """Verify a Merkle inclusion proof."""
        leaf_h = _leaf_hash(data)
        computed = leaf_h
        i = index
        n = len(self._leaf_hashes)

        for sibling in proof:
            if i % 2 == 1:
                computed = _node_hash(sibling, computed)
            else:
                computed = _node_hash(computed, sibling)
            i //= 2

        return computed == expected_root

    # ── private helpers ──────────────────────────────────────────────────────

    def _compute_root(self, hashes: list[bytes]) -> bytes:
        if len(hashes) == 1:
            return hashes[0]
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])  # duplicate last leaf (RFC 6962 convention)
        next_level = [
            _node_hash(hashes[i], hashes[i + 1])
            for i in range(0, len(hashes), 2)
        ]
        return self._compute_root(next_level)

    def _build_proof(self, hashes: list[bytes], index: int) -> list[bytes]:
        if len(hashes) == 1:
            return []
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        sibling = hashes[index ^ 1]
        parent_hashes = [
            _node_hash(hashes[i], hashes[i + 1])
            for i in range(0, len(hashes), 2)
        ]
        return [sibling] + self._build_proof(parent_hashes, index // 2)

    def to_dict(self) -> dict:
        return {
            "size": len(self.leaves),
            "root": self.root_hex(),
            "leaf_hashes": [h.hex() for h in self._leaf_hashes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MerkleTree":
        """Reconstruct tree from a persisted dict (leaves must be re-appended externally)."""
        tree = cls()
        for h in d.get("leaf_hashes", []):
            tree._leaf_hashes.append(bytes.fromhex(h))
        return tree
