import os
import json
import numpy as np
from PIL import Image
from common import print_progress_bar


def remove_background(img_path, bg_color=(252, 180, 191, 255)):
    img = Image.open(img_path).convert("RGBA")
    img_array = np.array(img)
    mask = (img_array[:, :, :3] == bg_color[:3]).all(axis=-1)
    img_array[mask] = [0, 0, 0, 0]
    Image.fromarray(img_array).save(img_path)


def segment_images(dataset_sort):
    if not dataset_sort or not os.path.exists(dataset_sort):
        raise NotADirectoryError("The dataset root path is either missing or invalid in the JSON file.")
    
    frames = [entry for entry in os.listdir(dataset_sort) if os.path.exists(os.path.join(dataset_sort, entry))]
    total = len(frames)
    for i, f in enumerate(frames):
        print_progress_bar(i, total, additional=f"Frame: {f}")
        dir_path = os.path.join(dataset_sort, f)
        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        for f in files:
            img_path = os.path.join(dir_path, f)
            sequence = f.split('-')[1]
            if sequence == "x": # The last frame is already transparent
                continue
            remove_background(img_path)
    print("")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    res_dir = os.path.abspath(os.path.join(script_dir, "resource"))
    bg_dir = os.path.abspath(os.path.join(res_dir, "foreground.png"))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_sort = os.path.join(dataset_root_path, "sorted")
    segment_images(dataset_sort)