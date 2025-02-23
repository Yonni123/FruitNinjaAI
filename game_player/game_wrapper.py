import cv2
import numpy as np
import mss
import time


class GameWrapper:
    def __init__(self, action_function, monitor_index=0):
        self.__action_function = action_function

        with mss.mss() as sct:
            if 0 <= monitor_index < len(sct.monitors):
                self.monitor = sct.monitors[monitor_index]
            else:
                raise ValueError(f"Invalid monitor index: {monitor_index}. Available: {len(sct.monitors) - 1}")
            
        self.__game_region = self.__get_game_region()

    def __get_game_region(self):
        """ Capture a scaled-down screen and let the user select a region by clicking two corners. """
        selected_game_corners = []
        mouse_callback_res = {
            "X": None,
            "Y": None,
            "E": None
        }

        def mouse_callback(event, x, y, flags, param):
            """ Mouse callback to capture selection points. """
            param["X"] = x  # Update x coordinate
            param["Y"] = y  # Update y coordinate
            param["E"] = event  # Update event

        is_inside_mouse_press = False
        with mss.mss() as sct:
            # Grab the screen to display
            screen = np.array(sct.grab(self.monitor))  
            screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

            height, width = screen.shape[:2]
            screen_resized = cv2.resize(screen, (width // 2, height // 2))

            instructions = "Left-click on the top-left corner of the game."
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.5
            font_color = (0, 255, 255)  # Yellow for better contrast
            line_thickness = 2
            background_color = (0, 0, 0)  # Black background for text

            # Create a blank image with the same size as the resized screen
            while len(selected_game_corners) < 2:
                # Display the screen in the resized window
                screen_resized = np.array(sct.grab(self.monitor))
                screen_resized = cv2.cvtColor(screen_resized, cv2.COLOR_BGRA2BGR)
                screen_resized = cv2.resize(screen_resized, (width // 2, height // 2))

                # Check for mouse click to select the corners
                if mouse_callback_res["E"] == cv2.EVENT_LBUTTONDOWN:
                    if not is_inside_mouse_press:
                        selected_game_corners.append((mouse_callback_res["X"], mouse_callback_res["Y"]))
                        instructions = "Now, left-click on the bottom-right corner."
                    is_inside_mouse_press = True
                
                if mouse_callback_res["E"] == cv2.EVENT_LBUTTONUP:
                    is_inside_mouse_press = False

                # Dynamically draw the rectangle as the user moves the mouse
                if len(selected_game_corners) == 1:
                    x1, y1 = selected_game_corners[0]
                    x2, y2 = mouse_callback_res["X"], mouse_callback_res["Y"]
                    # Fill the rectangle with lower alpha
                    filled_color = (0, 255, 0)  # Green for the fill
                    alpha = 0.2  # Low alpha for transparency in the fill (20% opacity)
                    overlay = screen_resized.copy()
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), filled_color, -1)  # -1 to fill the rectangle
                    # Blend the overlay with the original image
                    cv2.addWeighted(overlay, alpha, screen_resized, 1 - alpha, 0, screen_resized)
                    # Draw the rectangle border with 100% opacity
                    cv2.rectangle(screen_resized, (x1, y1), (x2, y2), (0, 255, 0), 1)  # Border with 100% opacity

                # Draw the instructions with a background
                cv2.putText(screen_resized, instructions, (10, 50), font, font_scale, background_color, line_thickness + 1, cv2.LINE_AA)
                cv2.putText(screen_resized, instructions, (10, 50), font, font_scale, font_color, line_thickness, cv2.LINE_AA)

                # Add a pulsing effect to the text for better visibility
                if time.time() % 1 > 0.5:
                    cv2.putText(screen_resized, instructions, (10, 50), font, font_scale, (255, 0, 0), line_thickness, cv2.LINE_AA)

                # Update window and wait
                cv2.imshow("Select two corners", screen_resized)
                cv2.setMouseCallback("Select two corners", mouse_callback, mouse_callback_res)
                cv2.waitKey(1)

        # Once the region is selected, process the coordinates and return the game region
        cv2.destroyAllWindows()
        x1, y1, x2, y2 = selected_game_corners[0][0] * 2, selected_game_corners[0][1] * 2, mouse_callback_res["X"] * 2, mouse_callback_res["Y"] * 2
        return {"top": min(y1, y2), "left": min(x1, x2), "width": abs(x2 - x1), "height": abs(y2 - y1)}


    def play(self):
        sct = mss.mss()
        counter = 0  # Millisecond counter
        fps = None

        while True:
            start_time = time.time()
            screen = np.array(sct.grab(self.__game_region))
            delta_time = (time.time() - start_time) * 1000
            counter += delta_time

            self.__action_function(screen, fps, counter, delta_time)

            fps = 1 / (time.time() - start_time)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


if __name__ == "__main__":
    def custom_take_action(screen, prev_FPS, counter, delta_time):
        frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
        prev_FPS = prev_FPS or 0    # in the first frame, there is no FPS

        cv2.setWindowTitle("GameFrame", f"FPS: {prev_FPS:.2f} - Counter: {counter:.2f} - dT: {delta_time:.2f} - Press Q to quit")
        cv2.imshow("GameFrame", frame)

    game = GameWrapper(custom_take_action, monitor_index=0)
    game.play()
