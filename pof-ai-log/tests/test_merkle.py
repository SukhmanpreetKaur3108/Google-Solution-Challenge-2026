"""Tests for the RFC 6962-style Merkle tree implementation."""

import hashlib
import pytest
from app.merkle import MerkleTree, _leaf_hash, _node_hash


def test_empty_tree_has_no_root():
    tree = MerkleTree()
    assert tree.root() is None


def test_single_leaf_root_equals_leaf_hash():
    tree = MerkleTree()
    data = b"hello"
    tree.append(data)
    assert tree.root() == _leaf_hash(data)


def test_two_leaves_root_is_node_of_leaf_hashes():
    tree = MerkleTree()
    tree.append(b"a")
    tree.append(b"b")
    expected = _node_hash(_leaf_hash(b"a"), _leaf_hash(b"b"))
    assert tree.root() == expected


def test_append_returns_correct_index():
    tree = MerkleTree()
    assert tree.append(b"x") == 0
    assert tree.append(b"y") == 1
    assert tree.append(b"z") == 2


def test_inclusion_proof_verifies_for_all_leaves():
    tree = MerkleTree()
    data_items = [f"cert-{i}".encode() for i in range(8)]
    for d in data_items:
        tree.append(d)
    root = tree.root()
    for i, d in enumerate(data_items):
        proof = tree.inclusion_proof(i)
        assert tree.verify_inclusion(d, i, proof, root), f"Proof failed for index {i}"


def test_tampered_data_fails_verification():
    tree = MerkleTree()
    tree.append(b"original")
    tree.append(b"other")
    root = tree.root()
    proof = tree.inclusion_proof(0)
    assert not tree.verify_inclusion(b"tampered", 0, proof, root)


def test_odd_number_of_leaves():
    tree = MerkleTree()
    for i in range(5):
        tree.append(f"leaf-{i}".encode())
    root = tree.root()
    for i in range(5):
        proof = tree.inclusion_proof(i)
        assert tree.verify_inclusion(f"leaf-{i}".encode(), i, proof, root)


def test_tree_is_append_only():
    tree = MerkleTree()
    tree.append(b"first")
    root_before = tree.root()
    tree.append(b"second")
    root_after = tree.root()
    assert root_before != root_after


def test_index_out_of_range_raises():
    tree = MerkleTree()
    tree.append(b"data")
    with pytest.raises(IndexError):
        tree.inclusion_proof(1)
    with pytest.raises(IndexError):
        tree.inclusion_proof(-1)
