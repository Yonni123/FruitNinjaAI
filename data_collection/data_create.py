import os
import json
import numpy as np
from PIL import Image

def get_sample_name(save_dir):
    existing_files = os.listdir(save_dir)
    
    # Filter out files that match the pattern 'img_<number>.ext' (assuming image extension is '.jpg', '.png', etc.)
    existing_numbers = []
    for file in existing_files:
        if file.startswith("img_"):
            try:
                # Extract the numeric part of the filename (assuming format 'img_<number>.ext')
                number = int(file.split('_')[1].split('.')[0])
                existing_numbers.append(number)
            except ValueError:
                continue  # Skip files that don't match the pattern
    
    # If there are no existing files, start with 0
    next_number = max(existing_numbers, default=-1) + 1
    
    # Return the new filename
    return f"img_{next_number}"  # Modify the extension as needed

def extract_seq(filename):
    #Extracts sequence number from filename.
    parts = filename.split('-')
    seq = parts[1] if len(parts) > 1 else "x"
    return int(seq) if seq.isdigit() else float('inf')

def extract_class(filename):
    if "Half" in filename:       
        return "B"  # Half fruits
    elif "Whole" in filename:    
        return "G"  # Fruits
    else:                   
        return "R"  # Bombs

def subtract_images(img1, img2):
    img1 = img1.convert("RGBA")
    img2 = img2.convert("RGBA")
    
    img1_data = img1.getdata()
    img2_data = img2.getdata()
    
    result_data = [
        (r2, g2, b2, a2) if a1 == 0 or (r1, g1, b1, a1) != (r2, g2, b2, a2) else (0, 0, 0, 0)
        for (r1, g1, b1, a1), (r2, g2, b2, a2) in zip(img1_data, img2_data)
    ]
    
    result = Image.new("RGBA", img1.size)
    result.putdata(result_data)
    
    return result

def add_mask_to_channel(input_image, channel, target_image=None):
    if input_image.mode != 'RGBA':
        input_image = input_image.convert('RGBA')
    input_array = np.array(input_image)
    alpha = input_array[:, :, 3]
    mask = (alpha != 0).astype(np.uint8) * 255

    if target_image is None:
        target_image = Image.new('RGB', input_image.size, (0, 0, 0))
    else:
        if target_image.mode != 'RGB':
            target_image = target_image.convert('RGB')

    # Convert the target image to a NumPy array
    target_array = np.array(target_image)

    # Add the mask to the specified channel
    if channel.upper() == 'R':
        target_array[:, :, 0] = np.maximum(target_array[:, :, 0], mask)
    elif channel.upper() == 'G':
        target_array[:, :, 1] = np.maximum(target_array[:, :, 1], mask)
    elif channel.upper() == 'B':
        target_array[:, :, 2] = np.maximum(target_array[:, :, 2], mask)
    else:
        raise ValueError("Invalid channel. Choose 'R', 'G', or 'B'.")

    final = Image.fromarray(target_array)
    return final

def create_mask(files, frame_path, dest_dir, img_name):
    img1 = Image.open(os.path.join(frame_path, files[0])).convert("RGBA")
    mask = add_mask_to_channel(img1, channel=extract_class(files[0]))
    for i, file in enumerate(files):
        if i == 0:
            continue
        if extract_seq(files[i]) == float('inf'):
            continue
        img1 = Image.open(os.path.join(frame_path, files[i-1])).convert("RGBA")
        img2 = Image.open(os.path.join(frame_path, files[i])).convert("RGBA")
        res = subtract_images(img1, img2)
        mask = add_mask_to_channel(res, channel=extract_class(files[i]), target_image=mask)
    save_dir = os.path.join(dest_dir, "masks")
    mask.save(os.path.join(save_dir, img_name))

# Join all the images together to create the final training sample
def create_image(background, frame_path, dest_dir):
    save_dir = os.path.join(dest_dir, "images")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    files = [f for f in os.listdir(frame_path) if os.path.isfile(os.path.join(frame_path, f))]
    files.sort(key=extract_seq)
    if not files:
        print("No images found.")
        return

    if extract_seq(files[0]) != 0 or len(files) < 2:
        return

    base_img = Image.open(background).convert("RGBA")
    base_array = np.array(base_img)
    for file in files:
        img = Image.open(os.path.join(frame_path, file)).convert("RGBA")
        img_array = np.array(img)
        overlay_alpha = img_array[..., 3] / 255.0
        base_array[..., :3] = (1 - overlay_alpha[..., None]) * base_array[..., :3] + overlay_alpha[..., None] * img_array[..., :3]
    final_img = Image.fromarray(base_array)
    
    img_name = get_sample_name(save_dir) + ".png"
    final_img.save(os.path.join(save_dir, img_name))

    create_mask(files, frame_path, dest_dir, img_name)

def print_progress_bar(iteration, total, length=50, additional = ""):
    percent = (iteration + 1) / total
    bar_length = int(length * percent)
    bar = "#" * bar_length + "-" * (length - bar_length)
    print(f"\rProcessing Frames: [{bar}] {percent*100:.2f}% ({iteration+1}/{total}) {additional}", end='', flush=True)


script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, ".."))

with open(os.path.join(root_dir, "settings.json"), "r") as file:
    settings = json.load(file)["settings"]
dataset_root_path = settings.get("datasetRootPath")
dataset_sort = os.path.join(dataset_root_path, "sorted")
dataset_data = os.path.join(dataset_root_path, "data")
background_path = os.path.join(root_dir, "data_collection/background.png")

if dataset_sort and os.path.exists(dataset_sort):
    frames = [entry for entry in os.listdir(dataset_sort) if os.path.exists(os.path.join(dataset_sort, entry))]
    total = len(frames)
    for i, f in enumerate(frames):
        print_progress_bar(i, total, additional=f"Frame: {f}")
        dir_path = os.path.join(dataset_sort, f)
        create_image(background_path, dir_path, dataset_data)
    print("")
    
    print("Training images created successfully.")
else:
    print("The dataset root path is either missing or invalid in the JSON file.")