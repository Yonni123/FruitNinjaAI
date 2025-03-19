import keyboard
from game_wrapper import GameWrapper
import cv2
import torch
from ultralytics import YOLO
from collections import defaultdict
import numpy as np
import os
import threading
import time
import pyautogui


playing = False  # Global variable to track whether the bot is active
lock = threading.Lock()


def toggle_playing():
    global playing
    playing = not playing
    print("Playing:" if playing else "Paused")

keyboard.add_hotkey("s", toggle_playing)  # Bind 'S' key to toggle playing

def predict_fruit_position(track_history, target_distance):
    """
    Predicts the future (X, Y) position of a fruit based on its movement history,
    assuming constant velocity.

    Parameters:
    - track_history: List of (X, Y, ms) tuples.
    - target_distance: Distance to predict ahead.

    Returns:
    - (predicted_x, predicted_y): Future coordinates.
    """
    if len(track_history) < 2:
        return None  # Need at least 2 points to determine direction

    # Get the last two positions
    x1, y1, _ = track_history[-2]
    x2, y2, _ = track_history[-1]

    # Compute direction
    dx, dy = x2 - x1, y2 - y1
    length = np.hypot(dx, dy)

    if length == 0:
        return x2, y2  # No movement, return the same position

    # Scale direction to target distance
    dx, dy = (dx / length) * target_distance, (dy / length) * target_distance

    return x2 + dx, y2 + dy

def gradual_move_to(x1, y1, x2, y2, steps=20, duration=0.2):
    """Moves the cursor gradually from (x1, y1) to (x2, y2)."""
    for i in range(1, steps + 1):
        # Calculate the intermediate position
        new_x = x1 + (x2 - x1) * (i / steps)
        new_y = y1 + (y2 - y1) * (i / steps)
        
        # Move the cursor to the new position
        pyautogui.moveTo(new_x, new_y, duration=duration / steps, _pause=False)


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    weights_path = "../detection_model/FruitNinja/YOLO11s/weights/best.pt"
    model = YOLO(weights_path).to(device)

    # Store the track history for each fruit
    track_history = defaultdict(lambda: [])
    current_fruits = []
    y_percentage_threshold = 0.1
    game_frame = None

    def track_fruits(self, screen, prev_FPS, time_ms, delta_time):
        global current_fruits, track_history, game_frame
        frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

        prev_FPS = prev_FPS or 0  # In the first frame, there is no FPS

        # Run YOLO tracking on the frame, persisting tracks between frames
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tracker_path = os.path.join(script_dir, "custom_tracker.yaml")
        results = model.track(frame, persist=True, verbose=False, tracker=tracker_path)

        game_frame = results[0].plot()
        orig_shape = results[0].orig_shape

        # Get the boxes and track IDs
        boxes = results[0].boxes.xywh.cpu()
        if results[0].boxes.id is None: # If no frames are detected
            cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
            cv2.imshow("GameFrame", game_frame)
            cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)
            return

        track_ids = results[0].boxes.id.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()

        with lock:
            current_fruits = []
            for box, track_id, class_id in zip(boxes, track_ids, class_ids):
                x, y, w, h = map(float, box)

                 # If fruits are not fully in the frame, bounding box is too noisy
                y_threshold = orig_shape[0] * y_percentage_threshold
                if y > orig_shape[0] - y_threshold:
                    continue

                # Half-fruits are not important
                if class_id % 2 != 1 and class_id != 20:    # 20 is bomb
                    continue    # Skip half fruits, they have even number

                track = track_history[track_id]
                track.append((x, y, time_ms))
                current_fruits.append([box, class_id, track_id])

        for box, track_id, class_id in zip(boxes, track_ids, class_ids):
            track = track_history[track_id]
            points = np.array([(p[0], p[1]) for p in track], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(game_frame, [points], isClosed=False, color=(230, 230, 230), thickness=1)

        # Clean up tracks that haven't been on screen for the last 5 seconds
        for track_id in list(track_history.keys()):
            if not track_history[track_id]:
                with lock:
                    del track_history[track_id]
                continue
            
            last_position_time = track_history[track_id][-1][2]
            if time_ms - last_position_time > 5000:
                with lock:
                    del track_history[track_id]

        # Display the annotated frame
        cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
        cv2.imshow("GameFrame", game_frame)
        cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)

    game = GameWrapper(track_fruits, monitor_index=0)

    
    def take_action():
        global current_fruits, track_history, game, game_frame
        while True:
            if not playing:
                time.sleep(1)
                continue
            
            with lock:
                fruits_copy = list(current_fruits)  # Copy to avoid modification issues
                track_history_copy = {k: v[:] for k, v in track_history.items()}  # Deep copy

            if fruits_copy == None or len(fruits_copy) == 0:
                time.sleep(0.05)
                continue

            for fruit in fruits_copy:
                box, class_id, track_id = fruit
                if class_id % 2 != 1 and class_id != 20:    # 20 is bomb
                    continue    # Skip half fruits, they have even number

                ms_into_the_future = 150 # This could definetly use a better name lol
                prediction = predict_fruit_position(track_history[track_id], ms_into_the_future)
                if prediction is None:
                    continue    # Not enough historical values to make prediction
                cv2.circle(game_frame, (int(prediction[0]), int(prediction[1])), 5, (0, 0, 255), -1)

                x, y, w, h = box

                spx, spy = map(float, game.game_to_screen_coords(prediction[0], prediction[1]))
                sx, sy = map(float, game.game_to_screen_coords(x, y))

                if class_id == 20:
                    # TODO: AVOID BOMBS
                    continue    # Skip bombs for now

                pyautogui.moveTo(spx, spy, duration=0.001, _pause=False)
                pyautogui.mouseDown(button='left', _pause=False)  
                gradual_move_to(spx, spy, sx, sy, steps=70, duration=0.35)
                pyautogui.mouseUp(button='left', _pause=False)
            time.sleep(0.05)


    action_thread = threading.Thread(target=take_action, daemon=True)
    action_thread.start()

    game.play()
