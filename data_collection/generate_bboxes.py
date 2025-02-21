import os
import json
import numpy as np
from PIL import Image
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common import print_progress_bar, get_bbox_from_mask


def generate_bbox_from_masks(masks_path, labels_path, image_name):
    txt_filename = os.path.join(labels_path, f"{image_name}.txt")
    masks = [entry for entry in os.listdir(masks_path) if os.path.exists(os.path.join(masks_path, entry))]
    with open(txt_filename, "w") as file:
        for mask in masks:
            mask_path = os.path.join(masks_path, mask)
            bbox = get_bbox_from_mask(mask_path)
            if bbox:
                class_id, x_center, y_center, width, height = bbox
                file.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")


def generate_bboxes(dataset_data):
    if not dataset_data or not os.path.exists(dataset_data):
        raise NotADirectoryError("The dataset data path is either missing or invalid in the JSON file.")

    frames = [entry for entry in os.listdir(dataset_data) if os.path.exists(os.path.join(dataset_data, entry))]
    total = len(frames)
    for i, f in enumerate(frames):
        print_progress_bar(i, total, additional=f"Frame: {f}")
        frame_path = os.path.join(dataset_data, f)
        masks_path = os.path.join(frame_path, "masks")
        generate_bbox_from_masks(masks_path, frame_path, f)
    print("")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_data = os.path.join(dataset_root_path, "data")
    generate_bboxes(dataset_data)
