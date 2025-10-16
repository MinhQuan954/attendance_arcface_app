# test_system.py
import sys
import cv2
import onnxruntime as ort
import importlib
from pathlib import Path

from config import FACES_DIR, EMBED_DIR, REPORTS_DIR, TMP_DIR, MODEL_NAME

def check_libs():
    print("Python:", sys.version)
    print("OpenCV:", cv2.__version__)
    print("ONNXRuntime:", ort.__version__)
    for m in ["insightface", "numpy", "pandas", "PIL"]:
        importlib.import_module(m)
        print("OK module:", m)

def check_camera(index=0):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError("Camera không mở được (index=%d)" % index)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise RuntimeError("Không đọc được frame từ camera.")
    print("OK camera, frame:", frame.shape)

def check_dirs():
    for p in [FACES_DIR, EMBED_DIR, REPORTS_DIR, TMP_DIR]:
        p.mkdir(parents=True, exist_ok=True)
        assert p.exists()
    print("OK folders.")

def check_insightface():
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name=MODEL_NAME, providers=["CPUExecutionProvider"])  # may download on first run
    app.prepare(ctx_id=0, det_size=(320,320))
    print("OK InsightFace model:", MODEL_NAME)

if __name__ == "__main__":
    print("=== System Test Start ===")
    check_libs()
    check_dirs()
    try:
        check_camera(0)
    except Exception as e:
        print("[WARN]", e)
    check_insightface()
    print("=== All basic checks passed (or warnings shown). ===")
