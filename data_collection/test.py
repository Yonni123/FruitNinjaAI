from PIL import Image
import os
import json

with open("settings.json", "r") as file:
    settings = json.load(file)["settings"]
dataset_root_path = settings.get("datasetRootPath")
directory = os.path.join(dataset_root_path, "raw")
dataset_sort = os.path.join(dataset_root_path, "sorted")

# Color to fill on the left side
fill_color = (252, 180, 191, 255)

for filename in os.listdir(directory):
    if "-x-" in filename:
        continue
    
    if filename.endswith('.png'):
        # Open image
        img_path = os.path.join(directory, filename)
        image = Image.open(img_path)
        pixels = image.load()

        # Modify pixels on the left side (x = 0 to 33)
        for y in range(image.height):
            for x in range(34):  # Filling from x=0 to x=33
                pixels[x, y] = fill_color

        # Overwrite the original image
        image.save(img_path)
        print(img_path)

print("Processing completed!")
