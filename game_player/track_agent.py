from game_wrapper import GameWrapper
import cv2
import torch
from ultralytics import YOLO
from collections import defaultdict
import numpy as np
import os


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    weights_path = "../detection_model/FruitNinja/YOLO11s/weights/best.pt"
    model = YOLO(weights_path).to(device)

    # Store the track history for each fruit
    track_history = defaultdict(lambda: [])
    y_percentage_threshold = 0.1

    def custom_take_action(screen, prev_FPS, time_ms, delta_time):
        frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

        prev_FPS = prev_FPS or 0  # In the first frame, there is no FPS

        # Run YOLO tracking on the frame, persisting tracks between frames
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tracker_path = os.path.join(script_dir, "custom_tracker.yaml")
        results = model.track(frame, persist=True, verbose=False, tracker=tracker_path)

        annotated_frame = results[0].plot()
        orig_shape = results[0].orig_shape

        # Get the boxes and track IDs
        boxes = results[0].boxes.xywh.cpu()
        if results[0].boxes.id is None:
            cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
            cv2.imshow("GameFrame", annotated_frame)
            cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)
            return

        track_ids = results[0].boxes.id.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()

        # Plot the tracks and velocity vectors
        for box, track_id, class_id in zip(boxes, track_ids, class_ids):
            x, y, w, h = map(float, box)

            # If fruits are not fully in the frame, bounding box is too noisy
            y_threshold = orig_shape[0] * y_percentage_threshold
            if y > orig_shape[0] - y_threshold:
                continue

            # Half-fruits are not important
            label = results[0].names[class_id]
            if "Half" in label:
                continue

            track = track_history[track_id]

            # Append the new position with velocity and timestamp
            track.append((x, y, time_ms))

            # Draw the tracking lines
            points = np.array([(p[0], p[1]) for p in track], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated_frame, [points], isClosed=False, color=(230, 230, 230), thickness=1)

        # Clean up tracks that haven't been on screen for the last 5 seconds
        for track_id in list(track_history.keys()):
            last_position_time = track_history[track_id][-1][2]
            if time_ms - last_position_time > 5000:
                del track_history[track_id]

        # Display the annotated frame
        cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
        cv2.imshow("GameFrame", annotated_frame)
        cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)

    game = GameWrapper(custom_take_action, monitor_index=0)
    game.play()
