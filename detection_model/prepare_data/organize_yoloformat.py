import os
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from common import get_classnames, print_progress_bar
import yaml
import random
import shutil
from pathlib import Path

def organize_yolo_format(data_dir, res_dir, split_ratio=None):
    """
    Organize data into YOLO format with train, val, and test splits.

    Args:
        data_dir (str): The directory containing the subfolders (img0, img1, ...) with images and labels.
        res_dir (str): The root directory where the organized files will be saved.
        split_ratio (dict, optional): A dictionary with split ratios for train, val, and test. Defaults to 70% train, 15% val, and 15% test.

    Returns:
        None
    """
    if split_ratio is None:
        split_ratio = {'train': 0.7, 'val': 0.15, 'test': 0.15}

    # Create the folders for images and labels under the root directory
    images_dir = Path(res_dir) / 'images'
    labels_dir = Path(res_dir) / 'labels'

    # Create subfolders for train, val, and test splits
    train_images_dir = images_dir / 'train'
    val_images_dir = images_dir / 'val'
    test_images_dir = images_dir / 'test'

    train_labels_dir = labels_dir / 'train'
    val_labels_dir = labels_dir / 'val'
    test_labels_dir = labels_dir / 'test'

    # Make sure all directories exist
    train_images_dir.mkdir(parents=True, exist_ok=True)
    val_images_dir.mkdir(parents=True, exist_ok=True)
    test_images_dir.mkdir(parents=True, exist_ok=True)

    train_labels_dir.mkdir(parents=True, exist_ok=True)
    val_labels_dir.mkdir(parents=True, exist_ok=True)
    test_labels_dir.mkdir(parents=True, exist_ok=True)

    # Collect all image and label pairs
    image_label_pairs = []

    for sub_folder in os.listdir(data_dir):
        sub_folder_path = os.path.join(data_dir, sub_folder)
        if os.path.isdir(sub_folder_path):
            for file in os.listdir(sub_folder_path):
                if file.endswith('.png'):
                    image_file = os.path.join(sub_folder_path, file)
                    label_file = os.path.splitext(image_file)[0] + '.txt'
                    if os.path.exists(label_file):
                        image_label_pairs.append((image_file, label_file))

    # Shuffle the list of image-label pairs
    random.shuffle(image_label_pairs)

    # Calculate the number of samples for each split
    total_samples = len(image_label_pairs)
    train_count = int(split_ratio['train'] * total_samples)
    val_count = int(split_ratio['val'] * total_samples)
    test_count = total_samples - train_count - val_count

    # Move files to appropriate directories and create text files for splits
    for i, (image_file, label_file) in enumerate(image_label_pairs):
        # Determine the target split
        if i < train_count:
            target_image_dir = train_images_dir
            target_label_dir = train_labels_dir
        elif i < train_count + val_count:
            target_image_dir = val_images_dir
            target_label_dir = val_labels_dir
        else:
            target_image_dir = test_images_dir
            target_label_dir = test_labels_dir

        # Move image and label files to the corresponding directory
        image_target = target_image_dir / os.path.basename(image_file)
        label_target = target_label_dir / os.path.basename(label_file)
        shutil.copy(image_file, image_target)
        shutil.copy(label_file, label_target)
        print_progress_bar(i, total_samples, additional="Moving files...")


    yaml_data = {
        'path': res_dir,  # dataset root directory
        'train': 'images/train',      # training images (relative to 'path')
        'val': 'images/val',          # validation images (relative to 'path')
        'test': 'images/test',        # optional test images (relative to 'path')
        'names': {i: name for i, name in enumerate(get_classnames())}  # class names
    }

    formatted_names = {}
    for idx, name in yaml_data['names'].items():
        formatted_names[idx] = name

    # Write the YAML configuration to a file
    yaml_data['names'] = formatted_names

    # Add comments to improve readability of the YAML
    yaml_file = Path(res_dir) / 'data.yaml'
    with open(yaml_file, 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

    print("Files have been organized into YOLO format.")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, "../.."))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_data = os.path.join(dataset_root_path, "data")
    results_dir = os.path.join(dataset_root_path, "YOLOformat")
    organize_yolo_format(dataset_data, results_dir)
