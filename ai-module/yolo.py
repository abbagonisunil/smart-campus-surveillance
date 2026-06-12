from ultralytics import YOLO

model = YOLO("yolov8n.pt")
model.predict(source=1, show=True, conf=0.5)