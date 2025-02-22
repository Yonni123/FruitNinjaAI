from game_wrapper import GameWrapper
import cv2
import torch
from ultralytics import YOLO


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    weights_path = "../detection_model/FruitNinja/YOLO11s/weights/best.pt"
    model = YOLO(weights_path).to(device)

    def custom_take_action(screen, prev_FPS=None):
        frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
        frame_name = "Game Frame"

        results = model.predict(source=frame, device=device, agnostic_nms=True, conf=0.5, verbose=False)
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = f"{result.names[int(box.cls[0])]} {box.conf[0]:.2f}"
                color = (0, 255, 0) if "Whole" in label else (255, 0, 0) if "Half" in label else (0, 0, 255) if "bomb" in label else (0, 0, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.setWindowTitle("GameFrame", f"{frame_name} - FPS: {prev_FPS:.2f}" if prev_FPS is not None else f"{frame_name} - FPS: N/A")
        cv2.imshow("GameFrame", frame)

    game = GameWrapper(custom_take_action, monitor_index=0)
    game.play()
    