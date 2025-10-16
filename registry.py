# registry.py
import os
from pathlib import Path
import numpy as np
import cv2
from typing import Dict, Tuple
from config import FACES_DIR, EMBED_DIR, SIM_THRESHOLD, TOPK
from utils import cosine_similarity

class Registry:
    def __init__(self):
        FACES_DIR.mkdir(parents=True, exist_ok=True)
        EMBED_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _embed_file(person: str) -> Path:
        return EMBED_DIR / f"{person}.npz"

    def list_people(self):
        return sorted([p.stem for p in EMBED_DIR.glob("*.npz")])

    def add_sample(self, person: str, embedding: np.ndarray, raw_bgr: np.ndarray):
        person = person.strip().replace(" ", "_")
        # append embedding
        ef = self._embed_file(person)
        if ef.exists():
            data = np.load(ef)
            vecs = data['vecs']
            vecs = np.vstack([vecs, embedding[None, :]])
        else:
            vecs = embedding[None, :]
        centroid = vecs.mean(axis=0)
        # L2 normalize for cosine shortcut
        centroid = centroid / (np.linalg.norm(centroid) + 1e-8)
        np.savez_compressed(ef, vecs=vecs.astype(np.float32), centroid=centroid.astype(np.float32))

        # save face image
        person_dir = FACES_DIR / person
        person_dir.mkdir(exist_ok=True, parents=True)
        n = len(list(person_dir.glob("*.jpg")))
        cv2.imwrite(str(person_dir / f"{person}_{n+1:03d}.jpg"), raw_bgr)

    def get_centroids(self) -> Dict[str, np.ndarray]:
        table = {}
        for f in EMBED_DIR.glob("*.npz"):
            data = np.load(f)
            table[f.stem] = data['centroid']
        return table

    def match(self, embedding: np.ndarray) -> Tuple[str, float]:
        """Return (best_name, best_similarity) or ("", 0.0) if none meet threshold."""
        cents = self.get_centroids()
        if not cents:
            return "", 0.0
        best_name = ""
        best_sim = -1.0
        for name, c in cents.items():
            sim = cosine_similarity(embedding, c)
            if sim > best_sim:
                best_sim = sim
                best_name = name
        if best_sim >= SIM_THRESHOLD:
            return best_name, float(best_sim)
        return "", float(best_sim)
