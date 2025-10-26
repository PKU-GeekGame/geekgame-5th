from Crypto.Util.number import bytes_to_long
from hashlib import shake_128
from secrets import token_bytes
from math import floor, ceil, log2
import os, enum

m = 256
w = 21
n = 128
l1 = ceil(m / log2(w))
l2 = floor(log2(l1*(w-1)) / log2(w)) + 1
l = l1 + l2

class HashType(enum.IntEnum):
    MSG = 0
    WOTS_PK = 1
    WOTS_CHAIN = 2
    TREE_NODE = 3

def F(data: bytes, seed: bytes, length: int, type: int) -> bytes:
    hasher = shake_128(seed + bytes([type]) + data)
    return hasher.digest(length)

class WOTS:
    def __init__(self, seed: bytes):
        self.seed = seed
        self.sk = [token_bytes(n // 8) for _ in range(l)]
        self.pk = [WOTS.chain(sk, w - 1, seed) for sk in self.sk]
    
    def sign(self, digest: bytes) -> bytes:
        assert 8 * len(digest) == m
        d1 = WOTS.pack(bytes_to_long(digest), l1, w)
        checksum = sum(w-1-i for i in d1)
        d2 = WOTS.pack(checksum, l2, w)
        d = d1 + d2

        sig = [WOTS.chain(self.sk[i], w - d[i] - 1, self.seed) for i in range(l)]
        return sig

    def get_pubkey_hash(self) -> bytes:
        return F(b"".join(self.pk), self.seed, 16, HashType.WOTS_PK)

    @staticmethod
    def pack(num: int, length: int, base: int) -> list[int]:
        packed = []
        while num > 0:
            packed.append(num % base)
            num //= base
        if len(packed) < length:
            packed += [0] * (length - len(packed))
        return packed
    
    @staticmethod
    def chain(x: bytes, n: int, seed: bytes) -> bytes:
        if n == 0:
            return x
        x = F(x, seed, 16, HashType.WOTS_CHAIN)
        return WOTS.chain(x, n - 1, seed)

    @staticmethod
    def verify(digest: bytes, sig: bytes, seed: bytes) -> bytes:
        d1 = WOTS.pack(bytes_to_long(digest), l1, w)
        checksum = sum(w-1-i for i in d1)
        d2 = WOTS.pack(checksum, l2, w)
        d = d1 + d2

        sig_pk = [WOTS.chain(sig[i], d[i], seed) for i in range(l)]
        return F(b"".join(sig_pk), seed, 16, HashType.WOTS_PK)

class MerkleTree:
    def __init__(self, height: int, seed: bytes):
        self.h = height
        self.seed = seed
        self.keys = [WOTS(seed) for _ in range(2**height)]
        self.tree = []
        self.root = self.build_tree([key.get_pubkey_hash() for key in self.keys])
    
    def build_tree(self, leaves: list[bytes]) -> bytes:
        self.tree.append(leaves)

        if len(leaves) == 1:
            return leaves[0]
        
        parents = []
        for i in range(0, len(leaves), 2):
            left = leaves[i]
            if i + 1 < len(leaves):
                right = leaves[i + 1]
            else:
                right = leaves[i]
            hasher = F(left + right, self.seed, 16, HashType.TREE_NODE)
            parents.append(hasher)
        
        return self.build_tree(parents)

    def sign(self, index: int, msg: bytes) -> list:
        digest = F(msg, self.seed, 32, HashType.MSG)
        key = self.keys[index]
        wots_sig = key.sign(digest)
        sig = [wots_sig]
        for i in range(self.h):
            leaves = self.tree[i]
            u = index >> i
            if u % 2 == 0:
                if u + 1 < len(leaves):
                    sig.append((0, leaves[u + 1]))
                else:
                    sig.append((0, leaves[u]))
            else:
                sig.append((1, leaves[u - 1]))
        return sig
    
    @staticmethod
    def verify(root, sig: list, msg: bytes, seed: bytes) -> bytes:
        digest = F(msg, seed, 32, HashType.MSG)
        wots_sig = sig[0]
        sig = sig[1:]
        pk_hash = WOTS.verify(digest, wots_sig, seed)
        computed_root = pk_hash
        for (side, leaf) in sig:
            if side == 0:
                computed_root = F(computed_root + leaf, seed, 16, HashType.TREE_NODE)
            else:
                computed_root = F(leaf + computed_root, seed, 16, HashType.TREE_NODE)
        return root == computed_root

def serialize_signature(sig) -> bytes:
    data = b"".join(sig[0])
    for side, node in sig[1:]:
        data += bytes([side]) + node
    return data

def deserialize_signature(data: bytes):
    sig = []
    sig.append([data[i*16:(i+1)*16] for i in range(l)])
    data = data[l*16:]
    height = (len(data)) // 17
    for i in range(height):
        side = data[i*17]
        node = data[i*17+1:(i+1)*17]
        sig.append((side, node))
    return sig
