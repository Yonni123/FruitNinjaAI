import pyautogui

def take_action(gamewrapper, fruits, track_history):
    """
    Takes appropriate actions in the game based on detected fruits and historical fruits.

    Parameters:
    gamewrapper (object): An instance of the game wrapper to be used to translate game coordinates to screen coordinates
    boxes (list): A list of bounding boxes for detected fruits and bombs. None if no fruits detected.
    track_ids (list): A list of tracking IDs corresponding to detected fruits, identifiers to the track history.
    class_ids (list): A list of class IDs representing fruit categories. Odd = whole fruit, Even = half fruit and 20 = bomb.
    track_history (dict): A dictionary storing the X and Y positions history of tracked fruits.
    """
    if fruits == None or len(fruits) == 0:
        return  # No fruits detected
    
    for i, fruit in enumerate(fruits):
        box, track_id, class_id = fruit
        if class_id % 2 == 0:
            if len(track_history[track_id]) > 1:
                x, y, w, h = box
                prev_x, prev_y, _ = track_history[track_id][-2]

                sx, sy = gamewrapper.game_to_screen_coords(x, y)
                spx, spy = gamewrapper.game_to_screen_coords(prev_x, prev_y)
                pyautogui.moveTo(spx, spy, _pause=False)
                pyautogui.dragTo(sx, sy, button='left', _pause=False)