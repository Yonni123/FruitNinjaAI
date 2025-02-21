import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common import extract_seq, get_last_filenum, empty_directory, copy_image


def sort_data(dataset_raw, dataset_sort, foreground=None, remove_corrupted_images=False):
    if not dataset_raw or not os.path.exists(dataset_raw):
        raise NotADirectoryError(f"Error: '{dataset_raw}' is not a directory.")
    if not dataset_sort or not os.path.exists(dataset_sort):
        raise NotADirectoryError(f"Error: '{dataset_sort}' is not a directory.")
    
    if not foreground:
        raise FileNotFoundError("Please provide a foreground")

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

    # Filter the files
    filtered_grouped_files = {}
    for frame, files in grouped_files.items():
        if len(files) == 0:
            continue
    
        files.sort(key=extract_seq)
        if extract_seq(files[0]) != 0:
            continue

        filtered_grouped_files[frame] = []
        filtered_grouped_files[frame].append(files[0])
        
        for i in range(1, len(files)):  
            if extract_seq(files[i]) != extract_seq(files[i - 1]) + 1:
                if extract_seq(files[i]) != float('inf'):
                    del filtered_grouped_files[frame]  # Remove the entire group
                    break
            filtered_grouped_files[frame].append(files[i])
    
    # Create a folder for each FRAME and move the files into the corresponding folder
    for frame, filenames in filtered_grouped_files.items():
        frame_num = get_last_filenum(dataset_sort, pattern="img_") + 1
        frame_folder = os.path.join(dataset_sort, "img_" + str(frame_num))
        
        # Create the folder if it doesn't exist
        if not os.path.exists(frame_folder):
            os.makedirs(frame_folder)
        else:
            empty_directory(frame_folder)
        
        # Move each file to its corresponding folder using os.rename
        for filename in filenames:
            src_path = os.path.join(dataset_raw, filename)
            dst_path = os.path.join(frame_folder, filename)
            os.rename(src_path, dst_path)
            print(f"Moved {filename} to {frame_folder}")
        
        if extract_seq(filenames[len(filenames)-1]) != float('inf'):
            dst_path = os.path.join(frame_folder, "x-x-EntireFrame.png")
            copy_image(foreground, dst_path)

    if remove_corrupted_images:
        empty_directory(dataset_raw, verbose=1)



if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    res_dir = os.path.abspath(os.path.join(script_dir, "resource"))
    bg_dir = os.path.abspath(os.path.join(res_dir, "foreground.png"))

    with open(os.path.join(root_dir, "settings.json"), "r") as file:
        settings = json.load(file)["settings"]
    dataset_root_path = settings.get("datasetRootPath")
    dataset_raw = os.path.join(dataset_root_path, "raw")
    dataset_sort = os.path.join(dataset_root_path, "sorted")
    sort_data(dataset_raw, dataset_sort, bg_dir, remove_corrupted_images=True)
