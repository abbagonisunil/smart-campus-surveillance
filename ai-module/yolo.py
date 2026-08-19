import os
import sys

try:
    from ultralytics import YOLO
except (ImportError, ModuleNotFoundError):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(os.path.dirname(script_dir), "venv", "bin", "python")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("Missing ultralytics. Please activate venv.", flush=True)
        sys.exit(1)

model = YOLO("yolov8n.pt")
# Source 1 is Mac built-in FaceTime HD camera
model.predict(source=1, show=True, conf=0.5)