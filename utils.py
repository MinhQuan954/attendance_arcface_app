# utils.py
import time
from datetime import datetime

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class CooldownKeeper:
    def __init__(self, seconds: int):
        self.seconds = seconds
        self._last = {}

    def ready(self, key: str) -> bool:
        t = time.time()
        last = self._last.get(key, 0)
        if t - last >= self.seconds:
            self._last[key] = t
            return True
        return False

def cosine_similarity(a, b):
    # expects L2-normalized vectors for speed
    return float((a * b).sum())
