# face_engine.py
from typing import List, Tuple
import numpy as np
import cv2
from insightface.app import FaceAnalysis
import onnxruntime as ort

from config import MODEL_NAME, DET_SIZE, PROVIDERS, EMB_NORM, MIN_FACE_SIZE

class FaceEngine:
    def __init__(self):
        # Ensure ONNXRuntime is available (CPU)
        assert 'CPUExecutionProvider' in ort.get_available_providers()
        self.app = FaceAnalysis(name=MODEL_NAME, providers=PROVIDERS)
        self.app.prepare(ctx_id=0, det_size=DET_SIZE)

    def detect_and_embed(self, bgr_image: np.ndarray):
        """Return list of (bbox, kps, det_score, embedding[512]) for each face."""
        faces = self.app.get(bgr_image)  # returns list with .bbox, .kps, .det_score, .normed_embedding
        results = []
        h, w = bgr_image.shape[:2]
        for f in faces:
            x1, y1, x2, y2 = [int(v) for v in f.bbox]
            if min(x2 - x1, y2 - y1) < MIN_FACE_SIZE:
                continue
            emb = f.normed_embedding if EMB_NORM else f.embedding / (np.linalg.norm(f.embedding) + 1e-8)
            results.append(((x1, y1, x2, y2), f.kps, float(f.det_score), emb.astype(np.float32)))
        return results

    def embed_crop(self, bgr_image: np.ndarray):
        """Embed the largest detected face. Return (embedding, bbox) or (None, None)."""
        dets = self.detect_and_embed(bgr_image)
        if not dets:
            return None, None
        dets.sort(key=lambda it: (it[0][2] - it[0][0]) * (it[0][3] - it[0][1]), reverse=True)
        bbox, kps, score, emb = dets[0]
        return emb, bbox

    @staticmethod
    def draw_bbox(img, bbox, name=None, sim=None):
        x1, y1, x2, y2 = bbox
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if name is not None:
            label = name
            if sim is not None:
                label += f" ({sim:.2f})"
            cv2.putText(img, label, (x1, max(y1-8, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2, cv2.LINE_AA)
        return img
