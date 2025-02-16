import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import random
import json


def __get_fruit_color(class_name, colors):
    for key in colors:
        if key.lower() in class_name.lower():  # Check if any key is a substring of fruit_name
            return np.array(colors[key], dtype=np.uint8)
    return np.array((128, 128, 128), dtype=np.uint8)    # Gray for unknown


def visualize_dataset(dataset_dir, disable_background=False, num_samples=2, max_masks=15, alpha=1):
    """
    Visualizes training images with their corresponding masks overlaid.
    Also draws bounding boxes around masked regions with class names.

    Args:
        dataset_dir (str): Root path of the dataset.
        num_samples (int): Number of samples to visualize.
        max_masks (int): Maximum number of masks to overlay per image.
        alpha (float): Transparency factor for blending masks (0 = invisible, 1 = opaque).
    """

    # Get all sample directories
    sample_dirs = [os.path.join(dataset_dir, d) for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d))]
    if not sample_dirs:
        print("No samples found in dataset directory.")
        return

    # Randomly select samples for visualization
    num_samples = min(num_samples, len(sample_dirs))
    selected_samples = random.sample(sample_dirs, num_samples)

    # Define colors for masks and bounding boxes
    mask_colors = {
        "watermelon": (255, 99, 71),    # Tomato Red
        "bomb": (255, 0, 0),            # Red
        "banana": (255, 255, 0),        # Yellow
        "blueberry": (0, 0, 255),       # Blue
        "orange": (255, 165, 0),        # Orange
        "lemon": (255, 255, 102),       # Light Yellow
        "coconut": (139, 69, 19),       # Brown
        "pineapple": (204, 174, 0),     # Darker Golden Yellow
        "apple": (55, 171, 0),           # Apple Green
        "kiwi": (85, 107, 47),          # Dark Olive Green
        "peach": (255, 180, 130),       # Soft Orange-Pink
        "mango": (255, 130, 0)          # Rich Yellow-Orange
    }

    # Create subplots
    _, axes = plt.subplots(num_samples, 2, figsize=(12, num_samples * 4))

    if num_samples == 1:
        axes = [axes]  # Ensure iterable in case of a single sample

    for idx, sample_dir in enumerate(selected_samples):
        # Load training image
        print(sample_dir)
        img_path = os.path.join(sample_dir, "final_image.png")
        if not os.path.exists(img_path):
            print(f"Image not found: {img_path}")
            continue

        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Load masks
        masks_dir = os.path.join(sample_dir, "masks")
        mask_files = [m for m in os.listdir(masks_dir) if m.endswith(('.png', '.jpg'))]

        overlay = image.copy()
        if disable_background:
            boxed_overlay = np.zeros_like(overlay)
        else:
            boxed_overlay = overlay.copy()

        for i, mask_file in enumerate(mask_files[:min(len(mask_files), max_masks)]):
            mask_path = os.path.join(masks_dir, mask_file)
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

            # Extract class name from filename (format: X-X-CLASSNAME.png)
            class_name = os.path.splitext(mask_file.split("-")[2])[0] or "Unknown"

            # Overlay mask
            color = __get_fruit_color(class_name, mask_colors)
            mask_indices = mask > 0

            # Blend colors instead of overwriting
            existing_colors = boxed_overlay[mask_indices]
            new_colors = color.astype(np.float32)

            if existing_colors.size > 0:
                blended_colors = (existing_colors.astype(np.float32) + new_colors) / 2
                boxed_overlay[mask_indices] = blended_colors.astype(np.uint8)
            else:
                boxed_overlay[mask_indices] = new_colors


            # Find contours for bounding boxes
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            #cv2.rectangle(boxed_overlay, (x, y), (x + w, y + h), tuple(color.tolist()), 2)
            cv2.rectangle(overlay, (x, y), (x + w, y + h), tuple(color.tolist()), 2)
            text_size = cv2.getTextSize(class_name, cv2.FONT_HERSHEY_SIMPLEX, 1, 3)[0]
            text_width, text_height = text_size

            # Check if text goes beyond the right or bottom edge
            text_x = x
            text_y = y - 5

            # Adjust text_x if the text is too far to the right
            if text_x + text_width > boxed_overlay.shape[1]:
                text_x = boxed_overlay.shape[1] - text_width - 5

            # Adjust text_y if the text is too far down
            if text_y - text_height < 0:
                text_y = y + h + 20  # Place text below the bounding box if there's not enough space above

            # Draw the text
            cv2.putText(boxed_overlay, class_name, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(color.tolist()), 3)
            cv2.putText(overlay, class_name, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, tuple(color.tolist()), 3)

        # Display images
        axes[idx][0].imshow(overlay)
        axes[idx][0].set_title(f"Original image ({os.path.basename(sample_dir)})")
        axes[idx][0].axis("off")

        axes[idx][1].imshow(boxed_overlay)
        axes[idx][1].set_title("Mask with Bounding Boxes")
        axes[idx][1].axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    with open("settings.json", "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_dir = os.path.join(dataset_root_path, "data")
    visualize_dataset(dataset_dir, disable_background=True)
