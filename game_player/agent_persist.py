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
import math
from collections import Counter


playing = False  # Global variable to track whether the bot is active
lock = threading.Lock()


def toggle_playing():
    global playing
    playing = not playing
    print("Playing:" if playing else "Paused")

keyboard.add_hotkey("s", toggle_playing)  # Bind 'S' key to toggle playing


def predict_fruit_position(track_history, target_time_ms, max_distance=90):
    """
    Predicts the future (X, Y) position of a fruit using parabolic motion,
    with an optional limit on how far the prediction can be from the current position.

    Parameters:
    - track_history: List of (X, Y, ms) tuples.
    - target_time_ms: Time in the future to predict, in milliseconds.
    - max_distance: Maximum allowed distance from the current position.

    Returns:
    - (predicted_x, predicted_y): Future coordinates.
    """
    if len(track_history) < 3:
        return None  # Not enough data to fit a parabola

    # Extract positions and timestamps
    xs = []
    ys = []
    ts = []

    for x, y, t in track_history:
        xs.append(x)
        ys.append(y)
        ts.append(t)

    # Convert to numpy arrays
    ts = np.array(ts, dtype=float)
    xs = np.array(xs, dtype=float)
    ys = np.array(ys, dtype=float)

    # Normalize time
    t0 = ts[-1]
    ts -= t0
    future_t = target_time_ms

    # Fit quadratic curves
    coeffs_x = np.polyfit(ts, xs, 2)
    coeffs_y = np.polyfit(ts, ys, 2)

    # Predict position at future_t
    raw_pred_x = np.polyval(coeffs_x, future_t)
    raw_pred_y = np.polyval(coeffs_y, future_t)

    # Clamp to max distance from last known point
    last_x = xs[-1]
    last_y = ys[-1]
    dx = raw_pred_x - last_x
    dy = raw_pred_y - last_y
    dist = np.hypot(dx, dy)

    if dist > max_distance:
        scale = max_distance / dist
        dx *= scale
        dy *= scale

    predicted_x = last_x + dx
    predicted_y = last_y + dy

    return predicted_x, predicted_y

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
def plot_game_frame(game_frame, fruits, class_ids):
    """ Annotates the game frame with bounding boxes and IDs. """

    for fruit, class_id in zip(fruits, class_ids):
        box, class_id, track_id = fruit
        color = (0, 255, 0) if class_id % 2 else (255, 0, 0)
        text = "Fruit" if class_id % 2 else "Half"
        text += f" {track_id}"
        if class_id == 20:
            color = (0, 0, 255)
            text = "Bomb"

        x, y, w, h = map(int, box)
        # Positions are middle of the box, move to top-left corner
        x -= w // 2
        y -= h // 2
        cv2.rectangle(game_frame, (x, y), (x + w, y + h), color, draw_width)
        cv2.putText(game_frame, text, (x, y - 5), font, 0.5, color, draw_width)
    return game_frame

def lines_intersect(p1, p2, q1, q2):
    def ccw(a, b, c):
        return (c[1]-a[1]) * (b[0]-a[0]) > (b[1]-a[1]) * (c[0]-a[0])
    return ccw(p1, q1, q2) != ccw(p2, q1, q2) and ccw(p1, p2, q1) != ccw(p1, p2, q2)

def line_intersects_circle(p1, p2, center, radius):
    x1, y1 = p1
    x2, y2 = p2
    cx, cy = center

    dx = x2 - x1
    dy = y2 - y1
    fx = x1 - cx
    fy = y1 - cy

    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    c = (fx * fx + fy * fy) - radius * radius

    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return False  # No intersection
    else:
        discriminant = math.sqrt(discriminant)
        t1 = (-b - discriminant) / (2 * a)
        t2 = (-b + discriminant) / (2 * a)
        return (0 <= t1 <= 1) or (0 <= t2 <= 1)
    
def get_detour_point(p1, p2, bomb_center, offset):
    """
    Returns a point offset to the side of the line p1 -> p2,
    centered around the bomb's position.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return p1  # Cannot define direction
    # Normal vector to line
    nx = -dy / length
    ny = dx / length
    # Offset around bomb center
    return (bomb_center[0] + nx * offset, bomb_center[1] + ny * offset)
    
def get_detour_path(start, target, bombs, danger_radius):
    """
    Computes a detour path from start to target that avoids all bombs.
    Returns a list of (x, y) points if a valid detour is found, otherwise None.
    """
    # Step 1: Find first bomb intersected
    blocking_bomb = None
    for bomb in bombs:
        center = (bomb[0][0], bomb[0][1])
        if line_intersects_circle(start, target, center, danger_radius):
            blocking_bomb = center
            break

    if not blocking_bomb:
        return None  # No detour needed

    # Step 2: Try left and right detours
    for sign in [+1, -1]:
        detour = get_detour_point(start, target, blocking_bomb, sign * danger_radius * 1.5)
        candidate_path = [detour, target]

        # Validate full detour path
        prev = start
        safe = True
        for pt in candidate_path:
            if any(line_intersects_circle(prev, pt, (b[0][0], b[0][1]), danger_radius) for b in bombs):
                safe = False
                break
            prev = pt

        if safe:
            return candidate_path

    return None  # No valid detour

def draw_path_on_frame(frame, path_points, color=(0, 255, 0), thickness=2):
    """
    Draws a path of line segments directly on the frame.

    Args:
        frame (np.ndarray): OpenCV image/frame (BGR).
        path_points (list of (x, y)): List of points in pixel coordinates.
        color (B, G, R): Line color (default green).
        thickness (int): Line thickness.
    """
    if len(path_points) < 2:
        return  # Nothing to draw

    for i in range(len(path_points) - 1):
        p1 = (int(path_points[i][0]), int(path_points[i][1]))
        p2 = (int(path_points[i + 1][0]), int(path_points[i + 1][1]))
        cv2.line(frame, p1, p2, color, thickness)

def move_if_mouse_on_bomb(game):
    screen_width, screen_height = pyautogui.size()
    screen_width, screen_height = game.screen_to_game_coords(screen_width, screen_height)
    third = screen_width / 3
    x, y = pyautogui.position()
    x, y = game.screen_to_game_coords(x, y)

    # Simulate mouse up (e.g., releasing the mouse button)
    pyautogui.mouseUp()
    time.sleep(0.1)  # Wait for a short time

    # Determine which third we're in
    if x < third:
        current_zone = 'left'
    elif x < 2 * third:
        current_zone = 'middle'
    else:
        current_zone = 'right'

    # Decide the furthest point to move to
    if current_zone == 'left':
        new_x = screen_width - 10  # Move near right edge
    elif current_zone == 'right':
        new_x = 10  # Move near left edge
    else:  # Middle
        new_x = 10 if x > screen_width / 2 else screen_width - 10

    new_x, y = game.game_to_screen_coords(new_x, y)
    pyautogui.moveTo(new_x, y, duration=0.001)  # Move smoothly


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
    y_percentage_threshold = 0.30    # If fruits are below 30% of the screen, ignore them.
    game_frame = None
    danger_zone = 100   # Just a global value so that fruit tracker can plot it, action thread will change this later.
    bombs_ms_into_future = 100       # How long into the future we want to predict the bomb. Too much could make it skip fruits.
                                    # This affects the dangerzone in the direction the bomb is moving.

    known_bombs = {}  # track_id -> (box, last_seen_time)
    track_classes = defaultdict(list)
    def track_fruits(self, screen, prev_FPS, time_ms, delta_time):
        global current_fruits, track_history, game_frame, danger_zone
        frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

        prev_FPS = prev_FPS or 0  # In the first frame, there is no FPS

        # Run YOLO tracking on the frame, persisting tracks between frames
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tracker_path = os.path.join(script_dir, "custom_tracker.yaml")
        resize_factor = 0.5  # Resize factor for faster processing
        frame_small = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)
        results = model.track(frame_small, persist=True, verbose=False, tracker=tracker_path)

        if results[0].boxes.id is None: # If no frames are detected
            cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
            cv2.imshow("GameFrame", frame)
            cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)
            return

        boxes = results[0].boxes.xywh.cpu()
        boxes = boxes * (1 / resize_factor)  # Scale back to original size
        track_ids = results[0].boxes.id.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()
        for track_id, class_id in zip(track_ids, class_ids):
            track_classes[track_id].append(class_id)

        orig_shape = frame.shape[:2]

        with lock:
            current_fruits = []
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
                    if y > orig_shape[0] * 0.95:
                        # Bomb was last seen near the bottom → predict just above it
                        ghost_y = orig_shape[0] * 0.9
                        prediction = (x, ghost_y)
                    else:
                        # Use motion prediction
                        prediction = predict_fruit_position(track, bombs_ms_into_future)
                    if prediction is not None:
                        new_box = (int(prediction[0]), int(prediction[1]), w, h)
                        new_bomb = (new_box, class_id, track_id)
                        new_bombs.append(new_bomb)
                        known_bombs[track_id] = ((x, y, w, h), time_ms, prediction)
            current_fruits.extend(new_bombs)

            active_ids = {f[2] for f in current_fruits}  # All currently visible track_ids

            for track_id in list(known_bombs.keys()):  # use list() to allow safe removal
                # If the ID is visible, check if it's still a bomb
                if track_id in active_ids:
                    recent_classes = track_classes.get(track_id, [])
                    if recent_classes:
                        majority_class = Counter(recent_classes).most_common(1)[0][0]
                        if majority_class != 20:
                            # No longer a bomb → remove from known bombs
                            del known_bombs[track_id]
                    continue  # either still a bomb or undecidable, skip ghosting
                
                # Not visible anymore → maybe ghost it
                last_box, last_seen_time, last_pred = known_bombs[track_id]
                x, y, w, h = last_box

                #if y > orig_shape[0] * 0.99:  # Fell off the screen
                #    del known_bombs[track_id]
                #    continue
                
                if time_ms - last_seen_time > 500:  # Too long unseen
                    del known_bombs[track_id]
                    continue
                
                # Add ghost bomb
                track = track_history[track_id]
                track.append((x, y, time_ms))
                current_fruits.append([last_box, 20, track_id])
                last_pred_box = (last_pred[0], last_pred[1], w, h)
                current_fruits.append([last_pred_box, 20, track_id])



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
        game_frame = plot_game_frame(frame, current_fruits, class_ids)
        draw_danger_zones(fruits = current_fruits,
                                   game_frame = game_frame,
                                   danger_zone_radius = danger_zone)
        cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {time_ms:.2f} - dT: {delta_time:.2f} - Press Q to quit")
        cv2.imshow("GameFrame", game_frame)
        cv2.setWindowProperty("GameFrame", cv2.WND_PROP_TOPMOST, 1)

    game = GameWrapper(track_fruits, monitor_index=0)
    
    def take_action():
        global current_fruits, track_history, game, game_frame, danger_zone

        # Calibration values:
        game_frame_w_to_danger_zone_radius_ratio = 0.110
        game_frame_w, game_frame_h = game.get_game_dimensions()
        danger_zone = int(game_frame_w * game_frame_w_to_danger_zone_radius_ratio)   # Radius around bombs in which we will not cut fruits

        wait_time_between_cuts = 0.001   # How long to wait between "cut groups". Triggered when there is a bomb present to be careful.
        cut_duration = 0.001             # How long each cut lasts. (ISH)
        pyautogui.PAUSE = 0.001          # After every pyautogui. This pause is needed for the game to register what happend
        fruits_ms_into_future = 60     # How long into the future we want to predict the fruit. Too much could be dangerous as it might hit a bomb

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
            mouse_x, mouse_y = pyautogui.position()
            mouse_x, mouse_y = game.screen_to_game_coords(mouse_x, mouse_y)

            # Check if mouse is inside a bomb, if so, Move somewhere else
            too_close = any(
                (mouse_x - bx) ** 2 + (mouse_y - by) ** 2 < danger_zone ** 2
                for bx, by, bw, bh in (b[0] for b in bombs)
            )
            if too_close:
                move_if_mouse_on_bomb(game)
                continue

            path_points = [] # Path to cut the fruits
            for fruit in fruits_copy:
                box, class_id, track_id = fruit
                if class_id % 2 != 1 or class_id == 20:
                    continue    # Skip half fruits and bombs, they have even number

                fruit_track = track_history_copy.get(track_id, [])
                if len(fruit_track) < 2 or (fruit_track[-1][2] - fruit_track[0][2]) < 50:
                    continue

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

                # We want to go from current mouse position to the predicted position
                path_points.append((mouse_x, mouse_y))
                if len(bombs) == 0:
                    path_points.append((prediction[0], prediction[1]))
                    path_points.append((x, y))
                    continue

                # Check if direct path intersects any bombs
                line_start = (mouse_x, mouse_y)
                line_end = (prediction[0], prediction[1])
                intersects = False   

                for bomb in bombs:
                    if line_intersects_circle(line_start, line_end, (bomb[0][0], bomb[0][1]), danger_zone):
                        intersects = True
                        break

                if not intersects:  # Go directly to fruit
                    path_points.append((prediction[0], prediction[1]))
                    path_points.append((x, y))
                else:   # Plan around the bomb
                    detour_path = get_detour_path((mouse_x, mouse_y), (prediction[0], prediction[1]), bombs, danger_zone)
                    if detour_path:
                        path_points.extend(detour_path)
                        path_points.append((x, y))
                

            for point in path_points:
                #pass
                pyautogui.mouseDown(button='left')
                spx, spy = map(float, game.game_to_screen_coords(point[0], point[1]))
                pyautogui.moveTo(spx, spy, duration=cut_duration)
            #draw_path_on_frame(game_frame, path_points)

            time.sleep(wait_time_between_cuts)


    action_thread = threading.Thread(target=take_action, daemon=True)
    action_thread.start()

    game.play()
    pyautogui.mouseUp(button='left')  # We will never let go of the mouse!
