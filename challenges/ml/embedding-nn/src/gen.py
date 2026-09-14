"""Generator for the embedding-nn challenge (embedding inversion).

We ship a token embedding table (each row is one token's vector, each token has
a character) and a sequence of noisy query vectors. Each query was produced by
taking one token's embedding and adding a little noise, so decoding a query is a
nearest-neighbour lookup in the table. Reading the decoded tokens in order
spells the flag.
"""

import numpy as np

FLAG = "NCTF{cosine_hop_walks_the_token_chain}"


def main():
    rng = np.random.default_rng(56789)

    # Vocabulary of printable characters used by the flag (+ decoy tokens).
    charset = sorted(set(FLAG) | set("abcdefghijklmnopqrstuvwxyz0123456789_{}"))
    vocab = list(charset)
    v = len(vocab)
    dim = 16

    # Well-separated embeddings so a small query perturbation cannot flip the
    # nearest neighbour.
    embeddings = rng.standard_normal((v, dim)) * 3.0
    char_of = {c: i for i, c in enumerate(vocab)}

    # Build one noisy query per flag character.
    queries = []
    for c in FLAG:
        base = embeddings[char_of[c]]
        noise = rng.standard_normal(dim) * 0.05
        queries.append(base + noise)
    queries = np.array(queries)

    np.savez(
        "embed_table.npz",
        embeddings=embeddings.astype(np.float64),
        token_char=np.array([ord(c) for c in vocab], dtype=np.int64),
        queries=queries.astype(np.float64),
    )
    print("wrote embed_table.npz  vocab", v, " queries", len(queries))


if __name__ == "__main__":
    main()
