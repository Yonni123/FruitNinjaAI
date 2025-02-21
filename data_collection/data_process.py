import os
import json
from data_sort import sort_data
from data_segment import segment_images
from data_create import create_images
from generate_masks import generate_masks
from generate_bboxes import generate_bboxes


def process_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    res_dir = os.path.abspath(os.path.join(script_dir, "resource"))
    fg_dir = os.path.abspath(os.path.join(res_dir, "foreground.png"))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_raw = os.path.join(dataset_root_path, "raw")
    dataset_data = os.path.join(dataset_root_path, "data")

    print("Sorting raw data...")
    sort_data(dataset_raw, dataset_data, fg_dir, remove_corrupted_images=True)
    print("Segmenting out the pink background...")
    segment_images(dataset_data)
    print("Creating images...")
    create_images(dataset_data, res_dir)
    print("Creating masks...")
    generate_masks(dataset_data)
    print("Creating bounding boxes...")
    generate_bboxes(dataset_data)
    print("Dataset done!")


if __name__ == "__main__":
    process_data()
    