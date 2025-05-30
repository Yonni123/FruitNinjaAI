import pyautogui
import pyperclip
import time
import keyboard  # For detecting key presses
from test2 import commands
import re

def rotate_coordinates(command):
    # Check if the command is "/setblock"
    if command.startswith("/setblock"):
        pattern = r"/setblock ~([-\d]*) ~([-\d]*) ~([-\d]*) (\S+)"

        match = re.search(pattern, command)
        if match:
            x = match.group(1) if match.group(1) else ''
            y = match.group(2) if match.group(2) else ''
            z = match.group(3) if match.group(3) else ''
            r = match.group(4) if match.group(4) else ''    # Rest

            final_command = f"/setblock ~{y} ~{x} ~{z} {r}"
            return final_command
        else: return command
        
    if command.startswith("/fill"):
        pattern = r"/fill ~([-\d]*) ~([-\d]*) ~([-\d]*) ~([-\d]*) ~([-\d]*) ~([-\d]*) (\S+)"
        match = re.search(pattern, command)
        if match:
            x1 = match.group(1) if match.group(1) else ''
            y1 = match.group(2) if match.group(2) else ''
            z1 = match.group(3) if match.group(3) else ''
            x2 = match.group(4) if match.group(4) else ''
            y2 = match.group(5) if match.group(5) else ''
            z2 = match.group(6) if match.group(6) else ''
            block = match.group(7) if match.group(7) else ''  # Block type

            final_command = f"/fill ~{y1} ~{x1} ~{z1} ~{y2} ~{x2} ~{z2} {block}"
            return final_command
        else: return command
    
    return command

def print_progress_bar(iteration, total, length=50, additional=""):
    """Print progress bar with iteration and percentage, overwriting the previous output."""
    percent = (iteration + 1) / total
    bar_length = int(length * percent)
    bar = "#" * bar_length + "-" * (length - bar_length)
    print(f"\rProcessing Frames: [{bar}] {percent*100:.2f}% ({iteration+1}/{total}) {additional}", end='', flush=True)


print("SWITCH!!")
time.sleep(5)  # Gives you time to switch to Minecraft
print("START!!")

delay_time = 0.05

for i, command in enumerate(commands):
    if keyboard.is_pressed("q"):  # Stop if "Q" is pressed
        print("Script stopped by user.")
        break

    pyautogui.press("t", _pause=False)  # Open chat
    time.sleep(delay_time)  # Add delay

    pyperclip.copy(rotate_coordinates(command))  # Copy command to clipboard
    pyautogui.hotkey("ctrl", "v", _pause=False)  # Paste command using Ctrl+V
    time.sleep(delay_time)  # Add delay

    pyautogui.press("enter", _pause=False)  # Execute command
    time.sleep(delay_time)  # Add delay

    # Update progress bar after each command
    print_progress_bar(i, len(commands), additional=f"Executing command {i+1}")

print("\nFinished or stopped.")