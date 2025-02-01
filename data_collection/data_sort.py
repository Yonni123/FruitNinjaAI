import os
import json

with open("../settings.json", "r") as file:
    settings = json.load(file)["settings"]
dataset_root_path = settings.get("datasetRootPath")
dataset_raw = os.path.join(dataset_root_path, "raw")
dataset_sort = os.path.join(dataset_root_path, "sorted")

if dataset_raw and os.path.exists(dataset_raw):
    # List all files in the dataset root path
    files = [f for f in os.listdir(dataset_raw) if os.path.isfile(os.path.join(dataset_raw, f))]
    
    # Filter the files to include only those with the format <FRAME>-<SEQUENCE>-<NAME>
    filtered_files = [f for f in files if len(f.split('-')) == 3]
    
    # Group the files by the FRAME part of the filename
    grouped_files = {}
    for filename in filtered_files:
        frame = filename.split('-')[0]
        if frame not in grouped_files:
            grouped_files[frame] = []
        grouped_files[frame].append(filename)
    
    # Create a folder for each FRAME and move the files into the corresponding folder
    for frame, filenames in grouped_files.items():
        frame_folder = os.path.join(dataset_sort, frame)
        
        # Create the folder if it doesn't exist
        if not os.path.exists(frame_folder):
            os.makedirs(frame_folder)
        
        # Move each file to its corresponding folder using os.rename
        for filename in filenames:
            src_path = os.path.join(dataset_raw, filename)
            dst_path = os.path.join(frame_folder, filename)
            os.rename(src_path, dst_path)
            print(f"Moved {filename} to {frame_folder}")
    
    print("Files have been grouped and moved successfully.")
else:
    print("The dataset root path is either missing or invalid in the JSON file.")