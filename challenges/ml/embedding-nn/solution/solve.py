"""Decode each noisy query to its nearest token and read the flag."""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "embed_table.npz")


def main():
    data = np.load(ART)
    emb = data["embeddings"]
    token_char = data["token_char"]
    queries = data["queries"]

    chars = []
    for q in queries:
        # Nearest embedding row (squared Euclidean distance).
        dist = np.sum((emb - q) ** 2, axis=1)
        idx = int(np.argmin(dist))
        chars.append(chr(int(token_char[idx])))

    print("".join(chars))


if __name__ == "__main__":
    main()
