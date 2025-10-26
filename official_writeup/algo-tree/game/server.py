from utils import *

FLAG = open("/flag").read().strip()

SEED = token_bytes(16)

height = 8
tree = MerkleTree(height, SEED)
used_indices = set()
root = tree.root

print("I wrote my own signing scheme using a Merkle tree! Can you break it?")
print(f"Seed: {SEED.hex()}")
print(f"Public key (root): {root.hex()}")

while True:
    action = input("Choose an action:\n1) Sign message\n2) Request flag\n> ").strip()
    if action == "1":
        ind = int(input("Index: "))
        msg = input("Message: ")
        if ind in used_indices:
            print("That index has already been used")
            continue
        if "flag" in msg:
            print("Nope")
            continue
        sig = tree.sign(ind, msg.encode())
        assert MerkleTree.verify(root, sig, msg.encode(), SEED)
        used_indices.add(ind)
        print(serialize_signature(sig).hex())
    elif action == "2":
        sig = deserialize_signature(bytes.fromhex(input("Signature: ")))
        if MerkleTree.verify(root, sig, b"Give me the flag", SEED):
            print(f"Congratulations! Here is your flag: {FLAG}")
        else:
            print("Verification failed...")
    else:
        continue
