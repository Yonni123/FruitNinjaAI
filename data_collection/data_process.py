import os
import json
from data_sort import sort_data


def process_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    res_dir = os.path.abspath(os.path.join(script_dir, "resource"))
    bg_dir = os.path.abspath(os.path.join(res_dir, "foreground.png"))
    fg_dir = os.path.abspath(os.path.join(res_dir, "foreground.png"))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_raw = os.path.join(dataset_root_path, "raw")
    dataset_sort = os.path.join(dataset_root_path, "sorted")

    sort_data(dataset_raw, dataset_sort, bg_dir, remove_corrupted_images=True)
    

if __name__ == "__main__":
    process_data()
    