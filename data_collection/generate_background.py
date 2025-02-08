import numpy as np
from PIL import Image
import random
import os


class BackgroundGen:
    def __init__(self, resource_path):
        if not os.path.exists(resource_path):
            raise FileNotFoundError(f"Error: Directory '{resource_path}' does not exist.")
        if not os.path.isdir(resource_path):
            raise NotADirectoryError(f"Error: '{resource_path}' is not a directory.")
        
        # Filter files only once
        self._files = [entry for entry in os.listdir(resource_path) if os.path.isfile(os.path.join(resource_path, entry))]
        
        splash_files = [file for file in self._files if "splash" in file]
        if not splash_files:
            raise FileNotFoundError("Error: No files matching 'splash' were found.")
        
        background = [file for file in self._files if file == "background.png"]
        if len(background) == 0:
            raise FileNotFoundError("Error: No 'background.png' file found.")
        
        # Preload background and splash images as numpy arrays
        self.__background = np.array(Image.open(os.path.join(resource_path, background[0])))
        self.__splashes = [np.array(Image.open(os.path.join(resource_path, splash))) for splash in splash_files]

    def generate_background(self, num_splashes=3):
        background_img = self.__background.copy()  # Start with the original background as a numpy array
        
        # Apply splashes
        for _ in range(num_splashes):
            splash_img = random.choice(self.__splashes)  # Choose a splash image randomly

            color_shift = np.random.randint(-255, 255, size=(3,))
            splash_img[..., :3] = np.clip(splash_img[..., :3] + color_shift, 0, 255)
            
            # Randomly select position to apply the splash
            max_x = background_img.shape[1] - splash_img.shape[1]
            max_y = background_img.shape[0] - splash_img.shape[0]
            x = random.randint(0, max_x)
            y = random.randint(0, max_y)

            # Apply splash image to the background
            # Blend images by updating the background pixel values
            splash_alpha = splash_img[:, :, 3] / 255.0 if splash_img.shape[2] == 4 else np.ones_like(splash_img[:, :, 0])
            for c in range(3):  # RGB channels
                background_img[y:y+splash_img.shape[0], x:x+splash_img.shape[1], c] = (
                    (1 - splash_alpha) * background_img[y:y+splash_img.shape[0], x:x+splash_img.shape[1], c] +
                    splash_alpha * splash_img[:, :, c]
                )

        return background_img


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    res_dir = os.path.abspath(os.path.join(script_dir, "resource"))
    bgg = BackgroundGen(resource_path=res_dir)
    final_background = Image.fromarray(bgg.generate_background())
    final_background.show()
