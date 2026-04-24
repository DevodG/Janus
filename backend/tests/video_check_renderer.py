"""
Visual Check Renderer.
Processes an image through the Janus FaceLandmarker and draws the results.
"""
import sys
import os
import cv2
import numpy as np
import mediapipe as mp

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

def run_visual_check(image_path, output_path):
    print(f"--- 👁️ Running Visual Check on {os.path.basename(image_path)} ---")
    
    from app.services.mmsa_engine import mmsa_engine
    mmsa_engine._lazy_load()
    
    # Load Image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        return

    from mediapipe.tasks.python.vision.core.image import Image
    mp_image = Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    # Detect
    result = mmsa_engine.landmarker.detect(mp_image)
    
    if result.face_landmarks:
        print(f"✅ Success: Detected {len(result.face_landmarks[0])} landmarks.")
        
        # Draw Landmarks (Modern way)
        # Note: Mediapipe Tasks API doesn't have the old drawing_utils in the same way.
        # We'll draw dots manually for the 'check'.
        for landmark in result.face_landmarks[0]:
            x = int(landmark.x * image.shape[1])
            y = int(landmark.y * image.shape[0])
            cv2.circle(image, (x, y), 2, (0, 255, 0), -1)
            
        cv2.imwrite(output_path, image)
        print(f"Saved visualization to: {output_path}")
    else:
        print("❌ No face detected in the image.")

if __name__ == "__main__":
    # Get the latest generated image from the artifact path
    input_img = "/Users/shashwat/.gemini/antigravity/brain/550dad57-1590-41e0-bed9-f1ab8c6b8ac3/visual_test_subject_1776892985215.png"
    output_img = "/Users/shashwat/.gemini/antigravity/brain/550dad57-1590-41e0-bed9-f1ab8c6b8ac3/video_check_result.png"
    
    run_visual_check(input_img, output_img)
