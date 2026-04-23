"""
Tri-Modal Verification Script.
Generates synthetic audio and video probes and tests the 3-way dissonance logic.
"""
import sys
import os
import wave
import struct
import numpy as np

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

def generate_probes():
    print("--- 🛠️ Generating Tri-Modal Probes ---")
    # 1. Audio Probe
    audio_path = "tests/test_audio.wav"
    with wave.open(audio_path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(struct.pack('h', 0) * 44100)
    
    # 2. Video Probe (using OpenCV)
    video_path = "tests/test_video.mp4"
    import cv2
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 10.0, (640, 480))
    for i in range(20):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw a circle to simulate facial movement
        cv2.circle(frame, (320 + i*5, 240), 50, (0, 255, 0), -1)
        out.write(frame)
    out.release()
    print(f"Generated: {audio_path}, {video_path}")
    return audio_path, video_path

def test_tri_modal():
    audio, video = generate_probes()
    print("\n--- 🧪 Tri-Modal Engine Verification ---")
    try:
        from app.services.mmsa_engine import mmsa_engine
        
        transcript = "I am ecstatic about this deal!"
        print(f"Scenario: '{transcript}' (Positive) with Audio/Video inputs.")
        
        result = mmsa_engine.analyze(audio, transcript, video)
        
        print("\nResults:")
        import json
        print(json.dumps(result, indent=2))
        
        if result.get("is_dissonant"):
            print("\n✅ Success: Tri-modal conflict detected via Maximum Pairwise Divergence.")
        else:
            print("\n⚠️ Note: Modalities aligned.")
            
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_tri_modal()
