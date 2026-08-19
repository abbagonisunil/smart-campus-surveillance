import os
import sys

# Auto-detect and switch to project virtualenv if executed with global python
try:
    import cv2
    import numpy as np
    import torch
    import socketio
    from ultralytics import YOLO
except (ImportError, ModuleNotFoundError):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(script_dir), "venv", "bin", "python"),
        os.path.join(script_dir, "venv", "bin", "python"),
        os.path.join(os.getcwd(), "venv", "bin", "python"),
    ]
    venv_python = next((p for p in candidates if os.path.exists(p)), None)
    if venv_python and sys.executable != venv_python:
        print(f"🔄 Switching to project virtual environment: {venv_python}", flush=True)
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("❌ Missing dependencies (socketio, cv2, ultralytics).", flush=True)
        print("Please run: ./venv/bin/python decoder.py OR source venv/bin/activate", flush=True)
        sys.exit(1)

import datetime
import time
import argparse

# Parse arguments
parser = argparse.ArgumentParser(description="Smart Campus YOLO Surveillance Decoder")
parser.add_argument("--source", type=str, default="auto", help="Camera index (0, 1), video file path, or 'demo' for simulation")
parser.add_argument("--headless", action="store_true", help="Run without cv2.imshow GUI window")
parser.add_argument("--server", type=str, default="http://localhost:5001", help="Backend socket server URL")
parser.add_argument("--conf", type=float, default=0.45, help="Confidence threshold (default: 0.45)")
parser.add_argument("--cooldown", type=int, default=5, help="Alert cooldown in seconds (default: 5)")
args = parser.parse_args()

# Socket.IO client with auto-reconnection
sio = socketio.Client(
    reconnection=True,
    reconnection_attempts=0, # Infinite attempts
    reconnection_delay=2,
    reconnection_delay_max=5
)

@sio.event
def connect():
    print("✅ Connected to backend Socket.IO server", flush=True)

@sio.event
def disconnect():
    print("📡 Disconnected from backend (will auto-reconnect)", flush=True)

@sio.event
def connect_error(data):
    pass

try:
    sio.connect(args.server)
except Exception as e:
    print(f"⚠️ Initial connection to backend failed: {e}. Will reconnect in background.", flush=True)

# Select hardware acceleration device (Apple Silicon MPS / CUDA / CPU)
if torch.backends.mps.is_available():
    device = "mps"
    print("⚡ Hardware Acceleration: Apple Silicon GPU (MPS) enabled", flush=True)
elif torch.cuda.is_available():
    device = "cuda"
    print("⚡ Hardware Acceleration: NVIDIA CUDA enabled", flush=True)
else:
    device = "cpu"
    print("💻 Hardware: CPU mode", flush=True)

# Resolve model path
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "yolov8n.pt")
if not os.path.exists(model_path):
    model_path = os.path.join(os.path.dirname(script_dir), "yolov8n.pt")
if not os.path.exists(model_path):
    model_path = "yolov8n.pt"

print(f"📦 Loading YOLO model: {model_path}", flush=True)
model = YOLO(model_path)

# Default normalized zone coordinates (percentages of frame width/height)
ZONE_RATIOS = [(0.30, 0.30), (0.90, 0.30), (0.90, 0.90), (0.30, 0.90)]
last_alert_time = 0
COOLDOWN_SECONDS = args.cooldown

def get_zone_pixels(frame_w, frame_h):
    return [(int(rx * frame_w), int(ry * frame_h)) for rx, ry in ZONE_RATIOS]

def is_in_zone(box, zone):
    # Check bottom-center (person's feet on ground) and center
    feet_x = int((box[0] + box[2]) / 2)
    feet_y = int(box[3])
    center_x = feet_x
    center_y = int((box[1] + box[3]) / 2)
    
    zone_poly = np.array(zone, dtype='float32')
    in_feet = cv2.pointPolygonTest(zone_poly, (feet_x, feet_y), False) >= 0
    in_center = cv2.pointPolygonTest(zone_poly, (center_x, center_y), False) >= 0
    return in_feet or in_center

# Initialize VideoCapture or Demo Mode
cap = None
demo_mode = False

if args.source == "demo":
    demo_mode = True
    print("🎬 Running in DEMO simulation mode", flush=True)
elif args.source in ["mac", "builtin", "laptop"]:
    # Force Mac built-in FaceTime camera (Index 1)
    cap = cv2.VideoCapture(1)
    if cap.isOpened():
        ret, test_frame = cap.read()
        if ret and test_frame is not None:
            print("📷 Using Mac Built-in Camera (Index 1)", flush=True)
        else:
            cap.release()
            cap = None
    if cap is None:
        print("⚠️ Could not open Mac built-in camera at Index 1, falling back to auto-detection...", flush=True)
elif args.source in ["phone", "iphone", "continuity"]:
    # Force Phone Continuity camera (Index 0)
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("📷 Using iPhone Continuity Camera (Index 0)", flush=True)
    else:
        cap.release()
        cap = None
elif args.source != "auto":
    try:
        src = int(args.source)
    except ValueError:
        src = args.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"⚠️ Could not open specified source {args.source}, falling back to auto-detection...", flush=True)
        cap = None

if cap is None and not demo_mode:
    # On Mac with iPhone nearby, Index 1 is Mac built-in webcam, Index 0 is iPhone Continuity Camera.
    # Check Index 1 first (Mac built-in camera), then Index 0.
    for cam_idx in [1, 0]:
        test_cap = cv2.VideoCapture(cam_idx)
        if test_cap.isOpened():
            ret, test_frame = test_cap.read()
            if ret and test_frame is not None:
                cap = test_cap
                cam_label = "Mac Built-in Camera" if cam_idx == 1 else "External / Continuity Camera"
                print(f"📷 Using {cam_label} (Index: {cam_idx})", flush=True)
                break
            test_cap.release()
    
    if cap is None:
        print("⚠️ No physical camera accessible. Switching to DEMO simulation mode...", flush=True)
        demo_mode = True

# Demo mode state variables
sim_x = 80
sim_y = 280
sim_dx = 5

print("🚀 Smart Campus Surveillance Module Active", flush=True)
if not args.headless:
    print("Press 'q' in the video window to quit, or Ctrl+C in terminal.", flush=True)

gui_enabled = not args.headless

try:
    while True:
        if demo_mode:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Draw campus background grid
            for gx in range(0, 640, 40):
                cv2.line(frame, (gx, 0), (gx, 480), (25, 35, 45), 1)
            for gy in range(0, 480, 40):
                cv2.line(frame, (0, gy), (640, gy), (25, 35, 45), 1)

            # Move simulated person back and forth
            sim_x += sim_dx
            if sim_x > 560 or sim_x < 60:
                sim_dx = -sim_dx

            # Draw simulated figure
            px, py = int(sim_x), int(sim_y)
            cv2.circle(frame, (px + 30, py - 40), 18, (200, 200, 200), -1)  # Head
            cv2.rectangle(frame, (px + 10, py - 20), (px + 50, py + 50), (180, 160, 100), -1)  # Torso
            cv2.rectangle(frame, (px + 15, py + 50), (px + 28, py + 100), (100, 100, 180), -1) # Leg 1
            cv2.rectangle(frame, (px + 32, py + 50), (px + 45, py + 100), (100, 100, 180), -1) # Leg 2
            time.sleep(0.03)  # ~30 FPS
        else:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("⚠️ Camera stream interrupted. Retrying in 0.5s...", flush=True)
                time.sleep(0.5)
                continue

        fh, fw = frame.shape[:2]
        zone_pixels = get_zone_pixels(fw, fh)

        # Run YOLOv8 detection: filter exclusively for person class (classes=[0]) with GPU acceleration
        results = model(frame, conf=args.conf, classes=[0], device=device, verbose=False)[0]

        # Draw restricted zone overlay
        cv2.polylines(frame, [np.array(zone_pixels)], True, (0, 0, 255), 2)
        cv2.putText(frame, "RESTRICTED ZONE (CAM-01)", (zone_pixels[0][0], max(20, zone_pixels[0][1] - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf_val = float(box.conf[0])
            color = (0, 255, 0)
            status_text = f"Person {conf_val:.2f}"

            if is_in_zone([x1, y1, x2, y2], zone_pixels):
                color = (0, 0, 255)
                status_text = f"INTRUSION DETECTED ({conf_val:.2f})"

                # Check alert cooldown
                if time.time() - last_alert_time > COOLDOWN_SECONDS:
                    alert = {
                        "type": "intrusion",
                        "message": "Person detected in restricted zone",
                        "timestamp": datetime.datetime.now().isoformat(),
                        "camera": "CAM-01"
                    }
                    if sio.connected:
                        try:
                            sio.emit("detection_alert", alert)
                            print(f"🚨 ALERT SENT: {alert['timestamp']} - {alert['message']}", flush=True)
                        except Exception as emit_err:
                            print(f"Socket emit error: {emit_err}", flush=True)
                    else:
                        print(f"⚠️ Alert generated but backend disconnected: {alert['message']}", flush=True)
                    last_alert_time = time.time()

            # Draw person bounding box and label
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, status_text, (x1, max(18, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Display window
        if gui_enabled:
            try:
                cv2.imshow("Smart Campus Surveillance - CAM-01", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception as gui_err:
                print(f"GUI display error: {gui_err}. Disabling display window.", flush=True)
                gui_enabled = False

except KeyboardInterrupt:
    print("\n🛑 Surveillance stopped by user.", flush=True)
finally:
    if cap is not None:
        cap.release()
    if gui_enabled:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    try:
        sio.disconnect()
    except Exception:
        pass
    print("👋 Cleaned up resources.", flush=True)