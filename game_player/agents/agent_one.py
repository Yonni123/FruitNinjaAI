import pyautogui
import time

def take_action(gamewrapper, boxes, track_ids, class_ids, track_history):
    print(class_ids)
    return
    for i, box in enumerate(boxes):
        # Check if the current object is a fruit (assuming 1 is the class_id for fruits)
        if class_ids[i] == 1:  # 1 = fruit (change based on actual class_id for fruit)
            # Get the coordinates of the fruit's bounding box
            x, y, width, height = box
            fruit_center_x = x + width // 2
            fruit_center_y = y + height // 2
            
            # Get the track history to predict future position (this is optional, use for more advanced strategies)
            if track_history and track_ids[i] in track_history:
                # Use track_history to predict next position, you can apply simple linear extrapolation
                history = track_history[track_ids[i]]
                if len(history) > 1:
                    # Get the last 2 positions to predict next move (simple linear prediction)
                    prev_x, prev_y = history[-2]
                    curr_x, curr_y = history[-1]
                    
                    # Calculate velocity (simple difference between last two points)
                    velocity_x = curr_x - prev_x
                    velocity_y = curr_y - prev_y
                    
                    # Predict the future position
                    future_x = curr_x + velocity_x
                    future_y = curr_y + velocity_y
                    
                    fruit_center_x = future_x
                    fruit_center_y = future_y

            # Convert the fruit's position to screen coordinates when moving the mouse
            fruit_center_x, fruit_center_y = gamewrapper.game_to_screen_coords(fruit_center_x, fruit_center_y)
            
            # Move the cursor to the predicted center of the fruit
            pyautogui.moveTo(fruit_center_x, fruit_center_y)
            
            # Simulate swipe (mouse down and move to simulate a slicing action)
            pyautogui.mouseDown()
            pyautogui.moveTo(fruit_center_x + 100, fruit_center_y + 100)  # Swipe in a direction (adjust as needed)
            pyautogui.mouseUp()

        # Handle bombs (if class_id == 2 or some other value, based on your game data)
        elif class_ids[i] == 2:  # 2 = bomb (change based on actual class_id for bombs)
            pass
            # Optionally, you can track bombs and avoid swiping at them.
            # For now, we simply ignore them, but you could add an "avoid" strategy here.

    # Sleep to simulate frame timing (adjust delay based on game speed)
    #time.sleep(0.1)
