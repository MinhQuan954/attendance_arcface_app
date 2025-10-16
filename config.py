# config.py
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "app" / "data"
FACES_DIR = DATA_DIR / "faces"
EMBED_DIR = DATA_DIR / "embeddings"
REPORTS_DIR = BASE_DIR / "app" / "reports"
TMP_DIR = BASE_DIR / "app" / "tmp"

# Thresholds & params
SIM_THRESHOLD = 0.38      # cosine similarity threshold for accept
MIN_FACE_SIZE = 50        # pixels (shorter side) to consider a face valid
ATTEND_COOLDOWN_SEC = 5   # min seconds between two scans of the same person
TOPK = 1                  # only use best match

# InsightFace
PROVIDERS = ["CPUExecutionProvider"]
MODEL_NAME = "buffalo_l"  # auto download on first run
DET_SIZE = (480, 480)       # detection input size (smaller => faster)
EMB_NORM = True             # L2-normalize embeddings before cosine

# UI
WINDOW_TITLE = "Attendance (ArcFace / InsightFace / CPU)"
CAM_INDEX = 0               # default webcam index
FPS_LIMIT = 15              # simple limiter for GUI preview
