import pyautogui

def gradual_move_to(x1, y1, x2, y2, steps=20, duration=0.2):
    """Moves the cursor gradually from (x1, y1) to (x2, y2)."""
    for i in range(1, steps + 1):
        # Calculate the intermediate position
        new_x = x1 + (x2 - x1) * (i / steps)
        new_y = y1 + (y2 - y1) * (i / steps)
        
        # Move the cursor to the new position
        pyautogui.moveTo(new_x, new_y, duration=duration / steps, _pause=False)

def take_action(gamewrapper, fruits, track_history):
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
        if class_id % 2 != 1:
            continue    # Skip half fruits

        if track_id not in track_history or len(track_history[track_id]) < 2:
            continue    # Not enough history

        x, y, w, h = box
        prev_x, prev_y = (x + w/2, y - h/2)

        spx, spy = map(float, gamewrapper.game_to_screen_coords(prev_x, prev_y))
        sx, sy = map(float, gamewrapper.game_to_screen_coords(x, y))

        pyautogui.moveTo(spx, spy, _pause=False)
        pyautogui.mouseDown(button='left', _pause=False)  
        gradual_move_to(spx,spy, sx, sy, steps=50, duration=0.3)
        pyautogui.mouseUp(button='left', _pause=False)

