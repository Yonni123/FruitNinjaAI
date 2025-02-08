import os
import json
import numpy as np
from PIL import Image
from generate_background import BackgroundGen
from common import print_progress_bar
import random


# Join all the images together to create the final training sample
foreground = os.path.dirname(os.path.abspath(__file__)) + "/resource/foreground.png"
def create_image(bgg, frame_path):
    files = [f for f in os.listdir(frame_path) if os.path.isfile(os.path.join(frame_path, f))]

    base_array = bgg.generate_background(num_splashes = random.randint(0, 5))
    for file in files:
        img = Image.open(os.path.join(frame_path, file)).convert("RGBA")
        img_array = np.array(img)
        overlay_alpha = img_array[..., 3] / 255.0
        base_array[..., :3] = (1 - overlay_alpha[..., None]) * base_array[..., :3] + overlay_alpha[..., None] * img_array[..., :3]

    final_img = Image.fromarray(base_array)
    
    img_path = os.path.join(frame_path, "final_image.png")
    final_img.save(img_path)

def create_images(dataset_sort):
    if not dataset_sort or not os.path.exists(dataset_sort):
        raise NotADirectoryError("The dataset root path is either missing or invalid in the JSON file.")

    frames = [entry for entry in os.listdir(dataset_sort) if os.path.exists(os.path.join(dataset_sort, entry))]
    total = len(frames)
    bgg = BackgroundGen(res_dir)

    for i, f in enumerate(frames):
        print_progress_bar(i, total, additional=f"Frame: {f}")
        dir_path = os.path.join(dataset_sort, f)
        create_image(bgg, dir_path)

    print("")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    res_dir = os.path.abspath(os.path.join(script_dir, "resource"))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_sort = os.path.join(dataset_root_path, "sorted")
    create_images(dataset_sort)