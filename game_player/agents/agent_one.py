import pyautogui
import numpy as np
import cv2

def gradual_move_to(x1, y1, x2, y2, steps=20, duration=0.2):
    """Moves the cursor gradually from (x1, y1) to (x2, y2)."""
    for i in range(1, steps + 1):
        # Calculate the intermediate position
        new_x = x1 + (x2 - x1) * (i / steps)
        new_y = y1 + (y2 - y1) * (i / steps)
        
        # Move the cursor to the new position
        pyautogui.moveTo(new_x, new_y, duration=duration / steps, _pause=False)

def predict_fruit_position(track_history, future_time_ms):
    """
    Predicts the future (X, Y) position of a fruit based on its movement history.

    Parameters:
    - track_history: List of (X, Y, ms) tuples.
    - future_time_ms: Time in the future (milliseconds) to predict.

    Returns:
    - (predicted_x, predicted_y): Future coordinates.
    """
    if len(track_history) < 5:
        return None  # Not enough data to predict motion

    # Extract time, X, Y
    times = np.array([entry[2] for entry in track_history])
    Xs = np.array([entry[0] for entry in track_history])
    Ys = np.array([entry[1] for entry in track_history])

    # Convert time to relative (start at 0)
    times = times - times[0]
    future_time = times[-1] + future_time_ms

    # Fit X as a linear function of time: X = a * t + b
    poly_x = np.polyfit(times, Xs, 1)  # 1st-degree polynomial (linear)
    predicted_x = np.polyval(poly_x, future_time)

    # Fit Y as a quadratic function of time: Y = a * t^2 + b * t + c
    poly_y = np.polyfit(times, Ys, 2)  # 2nd-degree polynomial (parabolic)
    predicted_y = np.polyval(poly_y, future_time)

    return predicted_x, predicted_y

def take_action(gamewrapper, fruits, track_history, game_frame):
    """
    Takes appropriate actions in the game based on detected fruits and historical fruits.

    Parameters:
    gamewrapper (object): An instance of the game wrapper to be used to translate game coordinates to screen coordinates
    fruits (list): A list of fruits currently on the screen with identifiers to the track history
    track_history (dict): A dictionary storing the X and Y positions history of tracked fruits.
    """
    if fruits == None or len(fruits) == 0:
        return  # No fruits detected
    
    for fruit in fruits:
        box, class_id, track_id = fruit
        if class_id % 2 != 1 and class_id != 20:    # 20 is bomb
            continue    # Skip half fruits, they have even number

        ms_into_the_future = 15 # This could definetly use a better name lol
        prediction = predict_fruit_position(track_history[track_id], ms_into_the_future)
        if prediction is None:
            continue    # Not enough historical values to make prediction
        cv2.circle(game_frame, (int(prediction[0]), int(prediction[1])), 5, (0, 0, 255), -1)

        x, y, w, h = box

        spx, spy = map(float, gamewrapper.game_to_screen_coords(prediction[0], prediction[1]))
        sx, sy = map(float, gamewrapper.game_to_screen_coords(x, y))

        if class_id == 20:
            # TODO: AVOID BOMBS
            continue    # Skip bombs for now

        pyautogui.moveTo(spx, spy, duration=0.001, _pause=False)
        pyautogui.mouseDown(button='left', _pause=False)  
        gradual_move_to(spx, spy, sx, sy, steps=70, duration=0.35)
        pyautogui.mouseUp(button='left', _pause=False)
