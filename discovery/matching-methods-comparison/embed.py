"""Embedding similarity with a local, open-weights text-embedding model.

The model name is read from EMBEDDING_MODEL (default below). No account and no key: the model is
downloaded on first use by the fastembed library and run on the CPU. If the library or the model
cannot be loaded this raises; compare.py records the method as not run and does not substitute
another way of scoring.
"""

import os
import time

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def model_name():
    return os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL)


class Embedder:
    def __init__(self, name=None):
        import numpy as np
        from fastembed import TextEmbedding
        self.np = np
        self.name = name or model_name()
        t0 = time.time()
        self.model = TextEmbedding(model_name=self.name)
        self.load_seconds = time.time() - t0
        self.embed_seconds = 0.0
        self.texts_embedded = 0

    def embed(self, texts):
        """Unit-length vectors, one row per text. The texts are lower-cased: captions are in capitals."""
        t0 = time.time()
        vecs = self.np.asarray(list(self.model.embed([t.lower() for t in texts])), dtype="float32")
        norms = self.np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.embed_seconds += time.time() - t0
        self.texts_embedded += len(texts)
        return vecs / norms


def similarity_matrix(np, quote_vecs, priority_vecs):
    """Cosine of every quote with every priority (rows quotes, columns priorities)."""
    return quote_vecs @ priority_vecs.T


def counts_at(np, matrix, levels):
    return [int((matrix >= lv).sum()) for lv in levels]


def top_n_cutoff(np, matrix, n):
    """The score of the n-th highest pair, and the (quote, priority) index pairs at or above it."""
    flat = matrix.ravel()
    n = min(n, flat.size)
    idx = np.argpartition(-flat, n - 1)[:n]
    cutoff = float(flat[idx].min())
    order = idx[np.argsort(-flat[idx])]
    cols = matrix.shape[1]
    return cutoff, [(int(i // cols), int(i % cols)) for i in order]
