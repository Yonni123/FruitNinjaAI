from game_wrapper import GameWrapper
import cv2
import torch
from ultralytics import YOLO
from collections import defaultdict
import numpy as np

# Function to predict the future positions of a fruit given its past positions
def predict_future_positions(positions, num_of_preds=10):
    predictions = []

    if len(positions) >= 3:  # Need at least 3 points for a quadratic fit
        x, y = zip(*positions)

        # Fit a quadratic polynomial (degree 2) to the x and y data
        x_coeffs = np.polyfit(x, y, 2)

        # Generate future x positions
        x_future = np.linspace(x[-1], x[-1] + num_of_preds * (x[-1] - x[-2]), num_of_preds)

        # Predict the corresponding y positions
        y_future = np.polyval(x_coeffs, x_future)

        # Store the future predictions
        predictions = list(zip(x_future, y_future))

    return predictions

if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    weights_path = "../detection_model/FruitNinja/YOLO11s/weights/best.pt"
    model = YOLO(weights_path).to(device)

    # Store the track history for each fruit
    track_history = defaultdict(lambda: [])

    def custom_take_action(screen, prev_FPS, time_ms, delta_time):
        frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

        prev_FPS = prev_FPS or 0  # In the first frame, there is no FPS

        # Run YOLO tracking on the frame, persisting tracks between frames
        results = model.track(frame, persist=True, verbose=False, tracker="botsort.yaml")

        annotated_frame = results[0].plot()

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
            x, y, w, h = box
            label = results[0].names[class_id]
            track = track_history[track_id]

            vx, vy = 0, 0  # Default velocity
            if len(track) > 0:
                (x_prev, y_prev, _, _, t_prev) = track[-1]  # Get last position
                dt = (time_ms - t_prev) / 1000  # Convert milliseconds to seconds
                if dt > 0:
                    vx, vy = (x - x_prev) / dt, (y - y_prev) / dt  # Compute velocity

            # Append the new position with velocity and timestamp
            track.append((float(x), float(y), vx, vy, time_ms))
            if len(track) > 20:  # Retain latest 20 entries
                track.pop(0)

            # Draw the tracking lines
            points = np.array([(p[0], p[1]) for p in track], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated_frame, [points], isClosed=False, color=(230, 230, 230), thickness=2)

            # Draw velocity vector
            if len(track) > 1:
                end_x, end_y = int(x + vx * 0.03), int(y + vy * 0.03)  # Scale for visualization
                cv2.arrowedLine(annotated_frame, (int(x), int(y)), (end_x, end_y), (0, 0, 255), 3, tipLength=0.3)

        # Display the annotated frame
        cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
        cv2.imshow("GameFrame", annotated_frame)
        cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)

    game = GameWrapper(custom_take_action, monitor_index=0)
    game.play()
