import os
import json
import numpy as np
from PIL import Image


def empty_directory(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))  # Remove files
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))  # Remove subdirectories

def extract_seq(filename):
    #Extracts sequence number from filename.
    parts = filename.split('-')
    seq = parts[1] if len(parts) > 1 else "x"
    return int(seq) if seq.isdigit() else float('inf')

def subtract_images(img1, img2):
    img1 = img1.convert("RGBA")
    img2 = img2.convert("RGBA")
    
    # Convert images to NumPy arrays
    arr1 = np.array(img1)
    arr2 = np.array(img2)
    
    # Extract alpha channels
    alpha1 = arr1[:, :, 3]
    
    # Find pixels where either alpha is zero or colors differ
    mask = (alpha1 == 0) | (arr1 != arr2).any(axis=-1)
    
    # Create result array: default to (0,0,0,0) and copy differing pixels
    result = np.zeros_like(arr2)
    result[mask] = arr2[mask]
    
    # Convert back to PIL image
    return Image.fromarray(result)

def separate_images(frame_path):
    files = [entry for entry in os.listdir(frame_path) if os.path.exists(os.path.join(frame_path, entry))]
    if len(files) == 0:             # Should at least have one file
        return
    
    files.sort(key=extract_seq)
    if extract_seq(files[0]) != 0:  # First class should have sequence 0
        return
    
    if extract_seq(files[len(files)-1]) != float('inf'):
        pass

    classes_path = os.path.join(frame_path, "classes")
    if not os.path.exists(classes_path):
        os.makedirs(classes_path)
    else:
        empty_directory(classes_path)

    img1 = Image.open(os.path.join(frame_path, files[0])).convert("RGBA")
    mask = img1.split()[3]
    mask.save(os.path.join(classes_path, files[0]))
    for i, file in enumerate(files):
        if i == 0:
            continue
        if extract_seq(files[i]) == float('inf'):
            continue
        img1 = Image.open(os.path.join(frame_path, files[i-1])).convert("RGBA")
        img2 = Image.open(os.path.join(frame_path, files[i])).convert("RGBA")
        res = subtract_images(img1, img2)
        mask = res.split()[3]
        mask.save(os.path.join(classes_path, files[i]))

    bomb = next((f for f in files if "bomb." in f), None)
    bombOutline = next((f for f in files if "bombO" in f), None)
    if bomb and bombOutline:    # We need to combine their masks
        bombPath = os.path.join(classes_path, bomb)
        bombOPath = os.path.join(classes_path, bombOutline)
        bombImg = Image.open(bombPath).convert("RGBA")
        bombOImg = Image.open(bombOPath).convert("RGBA")

        os.remove(bombPath)
        os.remove(bombOPath)

        bombArray = np.array(bombImg)
        bombOArray = np.array(bombOImg)
        bombMask = bombArray[:, :, 0] > 128
        bombOMask = bombOArray[:, :, 0] > 128

        combinedMask = np.logical_or(bombMask, bombOMask).astype(np.uint8) * 255
        combinedImage = Image.fromarray(combinedMask, mode="L")
        combinedImage.save(os.path.join(classes_path, "x-x-bomb.png"))

    

def print_progress_bar(iteration, total, length=50, additional = ""):
    percent = (iteration + 1) / total
    bar_length = int(length * percent)
    bar = "#" * bar_length + "-" * (length - bar_length)
    print(f"\rProcessing Frames: [{bar}] {percent*100:.2f}% ({iteration+1}/{total}) {additional}", end='', flush=True)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_sort = os.path.join(dataset_root_path, "sorted")

    if dataset_sort and os.path.exists(dataset_sort):
        frames = [entry for entry in os.listdir(dataset_sort) if os.path.exists(os.path.join(dataset_sort, entry))]
        total = len(frames)
        for i, f in enumerate(frames):
            print_progress_bar(i, total, additional=f"Frame: {f}")
            dir_path = os.path.join(dataset_sort, f)
            separate_images(dir_path)
        print("")

        print("Training images created successfully.")
    else:
        print("The dataset root path is either missing or invalid in the JSON file.")