#!/usr/bin/env python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.reset import reset_demo

if __name__ == "__main__":
    reset_demo()
    print("Pending demo state reset")
