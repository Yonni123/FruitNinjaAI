import os
import json
import numpy as np
from PIL import Image
from common import extract_seq, empty_directory, print_progress_bar


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

def generate_masks_from_frame(frame_path):
    files = [entry for entry in os.listdir(frame_path) if os.path.exists(os.path.join(frame_path, entry))]

    masks_dir = os.path.join(frame_path, "masks")
    if not os.path.exists(masks_dir):
        os.makedirs(masks_dir)
    else:
        empty_directory(masks_dir)

    img1 = Image.open(os.path.join(frame_path, files[0])).convert("RGBA")
    mask = img1.split()[3]
    mask.save(os.path.join(masks_dir, files[0]))
    for i in range(len(files)):
        if i == 0:
            continue
        if extract_seq(files[i]) == float('inf'):
            continue
        img1 = Image.open(os.path.join(frame_path, files[i-1])).convert("RGBA")
        img2 = Image.open(os.path.join(frame_path, files[i])).convert("RGBA")
        res = subtract_images(img1, img2)
        mask = res.split()[3]
        mask_array = np.array(mask)
        if np.count_nonzero(mask_array) >= 2:  # Some threshold
            mask.save(os.path.join(masks_dir, files[i]))

    bomb = next((f for f in files if "bomb." in f), None)
    bombOutline = next((f for f in files if "bombO" in f), None)
    if bomb and bombOutline:    # We need to combine their masks
        bombPath = os.path.join(masks_dir, bomb)
        bombOPath = os.path.join(masks_dir, bombOutline)
        if not os.path.exists(bombPath) or not os.path.exists(bombOPath):
            return  # Bomb is outside the frame

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
        combinedImage.save(os.path.join(masks_dir, "x-x-bomb.png"))
    elif bomb:
        print(f"Found only a bomb: {frame_path}")
    elif bombOutline:
        print(f"Found only a bomb outline: {frame_path}")

def generate_masks(dataset_sort):
    if not dataset_sort or not os.path.exists(dataset_sort):
        raise NotADirectoryError("The dataset root path is either missing or invalid in the JSON file.")

    frames = [entry for entry in os.listdir(dataset_sort) if os.path.exists(os.path.join(dataset_sort, entry))]
    total = len(frames)
    for i, f in enumerate(frames):
        print_progress_bar(i, total, additional=f"Frame: {f}")
        dir_path = os.path.join(dataset_sort, f)
        generate_masks_from_frame(dir_path)
    print("")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_sort = os.path.join(dataset_root_path, "data")
    generate_masks(dataset_sort)
