import cv2
import numpy as np
from ultralytics import YOLO
import socketio
import datetime
import time

sio = socketio.SimpleClient()
sio.connect('http://localhost:5001')
print("✅ Connected to backend")

model = YOLO("yolov8n.pt")

RESTRICTED_ZONE = [(200, 150), (600, 150), (600, 450), (200, 450)]
last_alert_time = 0  # cooldown tracker
COOLDOWN_SECONDS = 5

def is_in_zone(box, zone):
    cx = int((box[0] + box[2]) / 2)
    cy = int((box[1] + box[3]) / 2)
    result = cv2.pointPolygonTest(
        np.array(zone, dtype='float32'),
        (cx, cy), False
    )
    return result >= 0

cap = cv2.VideoCapture(1)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=0.5)[0]
    cv2.polylines(frame, [np.array(RESTRICTED_ZONE)], True, (0, 0, 255), 2)

    for box in results.boxes:
        cls = int(box.cls[0])
        label = model.names[cls]

        if label == "person":
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            color = (0, 255, 0)

            if is_in_zone([x1, y1, x2, y2], RESTRICTED_ZONE):
                color = (0, 0, 255)

                # Only send alert every 5 seconds
                if time.time() - last_alert_time > COOLDOWN_SECONDS:
                    alert = {
                        "type": "intrusion",
                        "message": "Person detected in restricted zone",
                        "timestamp": str(datetime.datetime.now()),
                        "camera": "CAM-01"
                    }
                    sio.emit("detection_alert", alert)
                    print("⚠️  ALERT sent:", alert["timestamp"])
                    last_alert_time = time.time()

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.imshow("Smart Campus Surveillance", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
sio.disconnect()