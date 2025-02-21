from ultralytics import YOLOv10
import torch
import cv2

# Load Model
model = YOLOv10.from_pretrained("jameslahm/yolov10n")

# Set device
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
print(f"Model is running on: {device}")

# Path to your dataset YAML file
data_path = r'D:\FruitNinjaDataset\YOLOformat\data.yaml'  # Replace with the path to your dataset YAML file

# Start training
if __name__ == "__main__":
    model.train(data=data_path, epochs=50, batch=16, imgsz=640, device=device)

# Evaluate the trained model (on validation set)
results = model.val()

# Inference on new images (after training)
image_paths = [
    r'C:/Users/yonan/Desktop/FruitNinjaAI/aa.jpg',
    r'C:/Users/yonan/Desktop/FruitNinjaAI/000000039769.jpg',
    r'D:/FruitNinjaDataset/data/img_1778/final_image.png'
]

# Run batch inference
results = model.predict(source=image_paths, device=device, batch=4)

# Display images with detections
for img_path, result in zip(image_paths, results):
    img = cv2.imread(img_path)  # Load original image
    for box in result.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])  # Get bounding box
        label = f"{result.names[int(box.cls[0])]} {box.conf[0]:.2f}"  # Get label & confidence
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Draw box
        cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)  # Add label
    
    cv2.imshow("Detection", img)  # Show image
    cv2.waitKey(0)  # Wait for keypress before showing next image

cv2.destroyAllWindows()  # Close all image windows
