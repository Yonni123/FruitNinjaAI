import os
import numpy as np
import yaml
from pathlib import Path
import cv2
import argparse


def get_classnames():
    return ['AppleGreenHalf', 'AppleGreenWhole', 'BananaHalf', 'BananaWhole', 
            'CoconutHalf', 'CoconutWhole', 'KiwifruitHalf', 'KiwifruitWhole', 
            'LemonHalf', 'LemonWhole', 'MangoHalf', 'MangoWhole', 
            'OrangeHalf', 'OrangeWhole', 'PeachHalf', 'PeachWhole', 
            'PineappleHalf', 'PineappleWhole', 'WatermelonHalf', 'WatermelonWhole', 
            'bomb']


def class_to_id():
    """Generate a dictionary mapping class names to unique IDs."""
    classnames = get_classnames()
    return {name: i for i, name in enumerate(classnames)}


def extract_classname_from_file(filename):
    return ''.join([char for char in filename.split("-")[-1].split(".")[0] if not char.isdigit()])


def get_bbox_from_mask(mask_path):
    """Extract bounding box from a mask image and return in the format: class_id center_x center_y width height (normalized)."""
    # Load mask image (single channel)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)  
    
    # Get image dimensions (height, width)
    height, width = mask.shape
    
    # Get the coordinates of all white pixels (non-zero pixels)
    white_pixels = np.where(mask > 0)  # This gives a tuple of row and column indices of white pixels
    
    if len(white_pixels[0]) == 0:  # If there are no white pixels in the mask
        return []
    
    # Find x1, x2, y1, y2 based on the white pixels
    x_min, x_max = np.min(white_pixels[1]), np.max(white_pixels[1])  # Columns (width direction)
    y_min, y_max = np.min(white_pixels[0]), np.max(white_pixels[0])  # Rows (height direction)
    
    # Bounding box width and height
    width_bbox = x_max - x_min
    height_bbox = y_max - y_min
    
    # Calculate the center of the bounding box
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    # Normalize the coordinates to be between 0 and 1
    center_x /= width
    center_y /= height
    width_bbox /= width
    height_bbox /= height

    # Get the class ID
    file_name = os.path.basename(mask_path)
    class_name = extract_classname_from_file(file_name)
    class_id = class_to_id().get(class_name, -1)  # Returns -1 if class not found
    
    return [class_id, center_x, center_y, width_bbox, height_bbox]


def copy_image(source_path: str, destination_path: str):
    image = cv2.imread(source_path)
    if image is None:
        raise FileNotFoundError(f"Failed to load image: {source_path}")
    cv2.imwrite(destination_path, image)


def print_progress_bar(iteration, total, length=50, additional=""):
    """Print progress bar with iteration and percentage."""
    percent = (iteration + 1) / total
    bar_length = int(length * percent)
    bar = "#" * bar_length + "-" * (length - bar_length)
    print(f"\rProcessing Frames: [{bar}] {percent*100:.2f}% ({iteration+1}/{total}) {additional}", end='', flush=True)


def preprocess_data(data_dir):
    """Preprocess images and masks for YOLO."""
    image_paths = []
    annotations = []
    
    total_folders = sum(1 for _ in Path(data_dir).iterdir() if _.is_dir())
    current_folder = 0  # To track progress
    
    for img_folder in Path(data_dir).iterdir():
        if img_folder.is_dir():
            current_folder += 1  # Update folder counter
            
            final_image_path = os.path.join(img_folder, "final_image.png")
            mask_folder = os.path.join(img_folder, "masks")
            
            # Get all mask files
            mask_files = [f for f in os.listdir(mask_folder) if f.endswith('.png')]
            
            for mask_file in mask_files:
                mask_path = os.path.join(mask_folder, mask_file)
                boxes = get_bbox_from_mask(mask_path)
                
                # Create annotation for each mask (each object)
                for box in boxes:
                    # Format: [class_id, x_center, y_center, width, height]
                    x, y, w, h = box
                    img = cv2.imread(final_image_path)
                    img_h, img_w = img.shape[:2]
                    
                    # Normalize box coordinates to [0, 1]
                    x_center = (x + w / 2) / img_w
                    y_center = (y + h / 2) / img_h
                    width = w / img_w
                    height = h / img_h
                    
                    # Use class from the mask filename (e.g., class1, class2)
                    # Get the class name and remove all digits
                    class_name = ''.join([char for char in mask_file.split("-")[-1].split(".")[0] if not char.isdigit()])
                    class_id = class_name  # Now class_id will simply be the cleaned class name
                    
                    annotation = [class_id, x_center, y_center, width, height]
                    
                    image_paths.append(final_image_path)
                    annotations.append(annotation)
            
            # Print progress bar after each folder is processed
            print_progress_bar(current_folder, total_folders, additional=f"Processed folder {current_folder}/{total_folders}")
    
    return image_paths, annotations


def save_yaml(image_paths, annotations, output_yaml="coco8.yaml"):
    """Save data in COCO format YAML."""
    data = {
        'train': image_paths,
        'val': image_paths,  # Split train/test/val as needed
        'nc': len(set([anno[0] for anno in annotations])),  # Number of classes
        'names': [f'class{i}' for i in range(1, len(set([anno[0] for anno in annotations])) + 1)],  # Class names
        'annotations': annotations
    }

    with open(output_yaml, 'w') as f:
        yaml.dump(data, f)


if __name__ == "__main__":
    # Preprocess the data and save the YAML
    data_dir = f"D:/FruitNinjaDataset/data"
    output_yaml = f"D:/FruitNinjaDataset/processed_data.yaml"
    image_paths, annotations = preprocess_data(data_dir)
    save_yaml(image_paths, annotations, output_yaml=output_yaml)
