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

draw_width = 2
def draw_danger_zones(fruits, game_frame, danger_zone_radius):
    for fruit in fruits:
        box, class_id, track_id = fruit
        if class_id != 20:
            continue
        x, y, w, h = box
        cv2.circle(game_frame, (int(x), int(y)), danger_zone_radius, (0, 0, 255), draw_width)
    return game_frame

font = cv2.FONT_HERSHEY_SIMPLEX
def plot_game_frame(game_frame, fruits, class_ids, confidences):
    """ Annotates the game frame with bounding boxes and IDs. """

    for fruit, class_id, conf in zip(fruits, class_ids, confidences):
        box, class_id, track_id = fruit
        color = (0, 255, 0) if class_id % 2 else (255, 0, 0)
        text_label = "Fruit" if class_id % 2 else "Half"
        if class_id == 20:
            color = (0, 0, 255)
            text_label = "Bomb"
        text = f"{text_label} {track_id} - {conf * 100:.0f}%"

        x, y, w, h = map(int, box)
        x -= w // 2
        y -= h // 2

        # Draw bounding box
        cv2.rectangle(game_frame, (x, y), (x + w, y + h), color, draw_width)

        # Determine text size
        font_scale = 0.5
        thickness = 1
        text_size, baseline = cv2.getTextSize(text, font, font_scale, thickness)
        text_w, text_h = text_size

        # Draw filled background rectangle for text
        cv2.rectangle(game_frame, (x, y - text_h - 6), (x + text_w + 2, y), (0, 0, 0), -1)

        # Draw text (white on black background)
        cv2.putText(game_frame, text, (x + 1, y - 3), font, font_scale, (255, 255, 255), thickness)

    return game_frame

def handle_vanishing_bombs(current_fruits, current_frame_bombs, last_frame_bombs, current_time, game_height, max_age_ms = 50):
    # Extract current bomb track IDs for quick lookup
    current_ids = {track_id for _, _, track_id, _ in current_frame_bombs}

    for box, class_id, track_id, last_seen in last_frame_bombs:
        if track_id not in current_ids:
            age = current_time - last_seen
            if age > max_age_ms:
                continue

            _, y, _, h = map(float, box)
            bottom_edge = y + h
            if bottom_edge >= (game_height-1):
                continue    # Fruit exited the screen
            
            current_fruits.append((box, class_id, track_id))  # Re-add vanished bomb
            current_frame_bombs.append((box, class_id, track_id, last_seen))

    # Update last_frame_bombs to reflect current frame
    last_frame_bombs.clear()
    last_frame_bombs.extend(current_frame_bombs)


if __name__ == "__main__":
    device = ""
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)} is available.")
        device = "cuda"
    else:
        print("No GPU available. Training will run on CPU.")
        print("This will be very slow, possibly unplayable, consider using a GPU.")
        device = "cpu"
    weights_path = "../detection_model/FruitNinja/YOLO11s/weights/best.pt"
    model = YOLO(weights_path).to(device)

    # Store the track history for each fruit
    track_history = defaultdict(lambda: [])
    current_fruits = []             # This includes bombs! where class id is 20
    y_percentage_threshold = 0.15    # If fruits are below 10% of the screen, ignore them.
    game_frame = None
    danger_zone = 100   # Just a global value so that fruit tracker can plot it, action thread will change this later.
    bombs_ms_into_future = 100       # How long into the future we want to predict the bomb. Too much could make it skip fruits.
                                    # This affects the dangerzone in the direction the bomb is moving.
    max_age_ms = 25     # Maximum time (ms) to retain a vanished bomb before discarding it (helps with brief misdetections)

    last_frame_bombs = []

    def track_fruits(self, screen, prev_FPS, time_ms, delta_time):
        global current_fruits, track_history, game_frame, danger_zone
        frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

        prev_FPS = prev_FPS or 0  # In the first frame, there is no FPS

        # Run YOLO tracking on the frame, persisting tracks between frames
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tracker_path = os.path.join(script_dir, "custom_tracker.yaml")
        resize_factor = 1  # Resize factor for faster processing
        frame_small = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)
        results = model.track(frame_small, persist=True, conf=0.01, verbose=False, tracker=tracker_path)

        if results[0].boxes.id is None: # If no frames are detected
            cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
            cv2.imshow("GameFrame", frame)
            cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)
            return

        boxes = results[0].boxes.xywh.cpu()
        boxes = boxes * (1 / resize_factor)  # Scale back to original size
        track_ids = results[0].boxes.id.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()
        confidences = results[0].boxes.conf.cpu().tolist()

        orig_shape = frame.shape[:2]

        current_frame_bombs = []
        for box, track_id, class_id in zip(boxes, track_ids, class_ids):
                if class_id == 20:
                    current_frame_bombs.append((box, class_id, track_id, time_ms))

        with lock:
            current_fruits = []
            handle_vanishing_bombs(current_fruits, current_frame_bombs, last_frame_bombs, time_ms, orig_shape[0], max_age_ms)
            new_bombs = []
            for box, track_id, class_id in zip(boxes, track_ids, class_ids):
                x, y, w, h = map(float, box)

                # If fruits are not fully in the frame, bounding box is too noisy
                y_threshold = orig_shape[0] * y_percentage_threshold
                if y > orig_shape[0] - y_threshold and class_id != 20:
                    continue

                track = track_history[track_id]
                track.append((x, y, time_ms))
                current_fruits.append([box, class_id, track_id])

                if class_id == 20:
                    current_frame_bombs.append((box, class_id, track_id, time_ms))
                    prediction = predict_fruit_position(track_history[track_id], bombs_ms_into_future)
                    if prediction is not None:
                        new_box = (int(prediction[0]), int(prediction[1]), w, h)
                        new_bomb = (new_box, class_id, track_id)
                        new_bombs.append(new_bomb)
            current_fruits.extend(new_bombs)
        # We are adding new "virtual" bomb in the direction the bomb is going (the prediction)
        # This makes the agent extra careful when it's "in front of" the bomb.

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

        game_frame = plot_game_frame(frame, current_fruits, class_ids, confidences)
        draw_danger_zones(fruits=current_fruits,
                          game_frame=game_frame,
                          danger_zone_radius=danger_zone)

        cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
        cv2.imshow("GameFrame", game_frame)
        cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)

    game = GameWrapper(track_fruits, monitor_index=0)
    
    def take_action():
        global current_fruits, track_history, game, game_frame, danger_zone

        # Calibration values:
        game_frame_w_to_danger_zone_radius_ratio = 0.125
        game_frame_w, game_frame_h = game.get_game_dimensions()
        danger_zone = int(game_frame_w * game_frame_w_to_danger_zone_radius_ratio)   # Radius around bombs in which we will not cut fruits

        wait_time_between_cuts = 0.20   # How long to wait between "cut groups". Triggered when there is a bomb present to be careful.
        cut_duration = 0.05             # How long each cut lasts.
        pyautogui.PAUSE = 0.01          # After every pyautogui. This pause is needed for the game to register what happend
        fruits_ms_into_future = 110     # How long into the future we want to predict the fruit. Too much could be dangerous as it might hit a bomb

        
        while True:
            if keyboard.is_pressed('q'):
                print("Q pressed, exiting...")
                break

            if not playing:
                time.sleep(1)
                continue
            
            with lock:
                fruits_copy = list(current_fruits)  # Copy to avoid modification issues
                track_history_copy = {k: v[:] for k, v in track_history.items()}  # Deep copy

            if fruits_copy == None or len(fruits_copy) == 0:
                time.sleep(0.05)
                continue

            bombs = [fruit for fruit in fruits_copy if fruit[1] == 20]
            for fruit in fruits_copy:
                box, class_id, track_id = fruit
                if class_id % 2 != 1:
                    continue    # Skip half fruits and bombs, they have even number

                x, y, w, h = box

                # Check if fruit is too close to a bomb
                too_close = any(
                    (x - bx) ** 2 + (y - by) ** 2 < danger_zone ** 2
                    for bx, by, bw, bh in (b[0] for b in bombs)
                )
                if too_close:
                    continue

                prediction = predict_fruit_position(track_history_copy[track_id], fruits_ms_into_future)
                if prediction is None:
                    continue    # Not enough historical values to make prediction
                
                # Check if prediction is too close to a bomb
                too_close = any(
                    (prediction[0] - bx) ** 2 + (prediction[1] - by) ** 2 < danger_zone ** 2
                    for bx, by, bw, bh in (b[0] for b in bombs)
                )
                if too_close:
                    continue

                spx, spy = map(float, game.game_to_screen_coords(prediction[0], prediction[1]))
                pyautogui.moveTo(spx, spy, duration=0)
                pyautogui.mouseDown(button='left')

                sx, sy = map(float, game.game_to_screen_coords(x, y))
                pyautogui.moveTo(sx, sy, duration=cut_duration)
                pyautogui.mouseUp(button='left')

                if bombs:
                    break

            time.sleep(wait_time_between_cuts)


    action_thread = threading.Thread(target=take_action, daemon=True)
    action_thread.start()

    game.play()
