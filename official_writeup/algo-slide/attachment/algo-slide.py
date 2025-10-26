from secrets import token_bytes
from hashlib import sha1
import base64

# THE FATE OF YOUR GRADE HANGS IN THE BALANCE...
# PROFESSOR'S CHALLENGE ECHOES IN YOUR MIND: "BREAK THIS CIPHER, GET 4.0!"


def pad(data_to_pad, block_size):
    # PADDING: BECAUSE EVEN REBELS NEED TO FOLLOW SOME RULES
    padding_len = block_size - len(data_to_pad) % block_size
    padding = bytes([padding_len] * padding_len)
    return data_to_pad + padding


def crypt(data: bytes, key: bytes, mode: str, rounds: int):
    # THE REBEL'S MASTERPIECE: DES CORE MUTILATED WITH SHA1 HEART TRANSPLANT
    # BLOCK SIZE: 4 BYTES (BECAUSE WHO NEEDS STANDARDS ANYWAY?)
    # KEY SIZE: 6 BYTES, 48 BITS (COMPROMISE IS THE NAME OF THE GAME)

    assert len(key) == 6  # THE CHAINS OF CONVENTION
    assert len(data) % 4 == 0  # CONFORMITY IN REBELLION
    assert mode == "e" or mode == "d"  # ENCRYPT OR DECRYPT? THE ETERNAL QUESTION

    res = bytearray()
    keys = [
        key[0:3],  # HALF A KEY FOR TWICE THE FUN
        key[3:6],  # THE OTHER HALF OF THIS DISASTER
    ]

    for i in range(0, len(data), 4):
        part = data[i : i + 4]
        L = part[0:2]  # LEFT HALF: INNOCENT BYSTANDER
        R = part[2:4]  # RIGHT HALF: ABOUT TO GET SHA1-MASHED

        for r in range(rounds):
            if mode == "e":
                round_key = keys[r % 2]  # KEY SCHEDULE: TOO SIMPLE TO FAIL?
            else:
                round_key = keys[
                    (r + 1) % 2
                ]  # DECRYPTION: WALKING BACKWARDS THROUGH CHAOS

            # THE MOMENT OF TRUTH: SHA1 AS FEISTEL FUNCTION
            # THIS IS WHERE THE REBEL'S DREAM MEETS CRYPTOGRAPHIC REALITY
            temp = sha1(R + round_key).digest()  # HASHING OUR WAY TO GLORY (OR RUIN)

            # THE FEISTEL DANCE: SWAP AND MUTATE
            L, R = R, bytes(
                [a ^ b for a, b, in zip(L, temp)]
            )  # XOR: THE BUTTERFLY EFFECT

        enc = R + L  # FINAL SWAP: THE GRAND ILLUSION
        res += enc  # COLLECTING THE PIECES OF OUR BROKEN DREAMS

    return bytes(res)  # BEHOLD: THE MONSTROSITY IN ALL ITS GLORY


def encrypt(data: bytes, key: bytes):
    # ENTER THE DRAGON: 32 ROUNDS OF PSEUDO-SECURITY
    return crypt(data, key, "e", 32)


def decrypt(data: bytes, key: bytes):
    # REVERSE THE CURSE: CAN WE UNDO THIS MADNESS?
    return crypt(data, key, "d", 32)


# THE ARENA: WHERE GRADES ARE WON AND DREAMS DIE
mode = input("easy or hard?")  # CHOOSE YOUR FATE, BRAVE SOUL

if mode == "easy":
    # EASY MODE: THE PROFESSOR'S WARM-UP LAUGH
    key = token_bytes(6)  # RANDOM KEY: THE DICE OF DESTINY
    flag_easy = open("/flag_easy", encoding="utf-8").read().strip()
    plain = pad(base64.b16encode(flag_easy.encode()), 4)
    enc_flag = encrypt(plain, key)  # THE FIRST VICTIM OF OUR CRYPTO-EXPERIMENT
    assert (
        decrypt(enc_flag, key) == plain
    )  # SANITY CHECK: EVEN MAD SCIENTISTS HAVE STANDARDS
    print(enc_flag.hex())  # THE CHALLENGE: CRACK THIS AND CLAIM YOUR REWARD

    # THE TRAINING GROUNDS: PRACTICE MAKES PERFECT (OR BREAKS SPIRITS)
    # HINT: YOU CAN SEND DATA IN BATCH TO SPEED UP IO
    while True:
        plain = bytes.fromhex(input())
        print(encrypt(plain, key).hex())  # THE ORACLE SPEAKS: ENCRYPTION ON DEMAND

elif mode == "hard":
    # HARD MODE: THE PROFESSOR'S FINAL LAUGH
    key = token_bytes(6)  # ANOTHER RANDOM KEY: DOUBLE THE TROUBLE
    flag_hard = open("/flag_hard", encoding="utf-8").read().strip()
    flag_hard_padded = pad(flag_hard.encode(), 4)
    xor_key = token_bytes(len(flag_hard_padded))  # EXTRA LAYER OF CONFUSION
    scrambled = bytes(
        [a ^ b for a, b in zip(flag_hard_padded, xor_key)]
    )  # MIXING THE POT

    # DOUBLE ENCRYPTION: BECAUSE ONE LAYER OF INSANITY WASN'T ENOUGH
    enc_scrambled = encrypt(scrambled, key)  # THE MAZE
    enc_xor_key = encrypt(xor_key, key)  # THE KEY TO THE MAZE (ENCRYPTED, OF COURSE)
    print(enc_scrambled.hex())  # THE FIRST CLUE IN THIS TREASURE HUNT
    print(enc_xor_key.hex())  # THE SECOND CLUE: NOW PUT THEM TOGETHER

    # THE GAUNTLET: 100,000 CHANCES TO PROVE YOUR WORTH
    # HINT: YOU CAN SEND MULTIPLE LINES BEFORE WAITING FOR RESPONSE TO SPEED UP IO
    for i in range(100000):
        plain = bytes.fromhex(input())
        print(encrypt(plain[:4], key).hex())  # THE ORACLE WHISPERS: ONE BLOCK AT A TIME

# THE CLOCK IS TICKING... CAN YOU BREAK THE REBEL'S CIPHER BEFORE YOUR GRADE SHATTERS?
# THE PROFESSOR WATCHES, AMUSED. THE BALL IS IN YOUR COURT.
