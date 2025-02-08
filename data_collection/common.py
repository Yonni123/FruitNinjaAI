import os
from PIL import Image


def get_last_filenum(save_dir, pattern="img_"):
    existing_files = os.listdir(save_dir)
    
    # Filter out files that match the pattern 'img_<number>.ext' (assuming image extension is '.jpg', '.png', etc.)
    existing_numbers = []
    for file in existing_files:
        if file.startswith(pattern):
            try:
                # Extract the numeric part of the filename (assuming format 'img_<number>.ext')
                number = int(file.split('_')[1].split('.')[0])
                existing_numbers.append(number)
            except ValueError:
                continue  # Skip files that don't match the pattern
    
    return max(existing_numbers, default=-1)

def empty_directory(directory, verbose=0):
    for root, dirs, files in os.walk(directory, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)  # Remove files
            if verbose:
                print(f"Removed file: {file_path}")
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            os.rmdir(dir_path)  # Remove subdirectories
            if verbose:
                print(f"Removed directory: {dir_path}")
    if verbose:
        print(f"Emptied directory: {directory}")

def extract_seq(filename):
    #Extracts sequence number from filename.
    parts = filename.split('-')
    seq = parts[1] if len(parts) > 1 else "x"
    return int(seq) if seq.isdigit() else float('inf')

def print_progress_bar(iteration, total, length=50, additional = ""):
    percent = (iteration + 1) / total
    bar_length = int(length * percent)
    bar = "#" * bar_length + "-" * (length - bar_length)
    print(f"\rProcessing Frames: [{bar}] {percent*100:.2f}% ({iteration+1}/{total}) {additional}", end='', flush=True)


def copy_image(src, dst):
    img = Image.open(src)  # Open the image
    img.save(dst)  # Save it to the new location
