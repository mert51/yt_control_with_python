import cv2
import mediapipe as mp
import pyautogui
import time
import math
import os

# Suppress MediaPipe warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# Finger landmarks
THUMB = 4
INDEX = 8
MIDDLE = 12
RING = 16
PINKY = 20

def calculate_distance(landmark1, landmark2, width, height):
    x1 = landmark1.x * width
    y1 = landmark1.y * height
    x2 = landmark2.x * width
    y2 = landmark2.y * height
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def fingers_touching(landmarks, finger_id, width, height, threshold=35):
    thumb = landmarks[THUMB]
    finger = landmarks[finger_id]
    distance = calculate_distance(thumb, finger, width, height)
    return distance < threshold, distance

def middle_finger_gesture(landmarks):
    middle_tip = landmarks[MIDDLE]
    middle_pip = landmarks[11]
    index_tip = landmarks[INDEX]
    index_pip = landmarks[6]
    ring_tip = landmarks[RING]
    ring_pip = landmarks[14]
    pinky_tip = landmarks[PINKY]
    pinky_pip = landmarks[18]
    
    middle_up = middle_tip.y < middle_pip.y
    index_down = index_tip.y > index_pip.y
    ring_down = ring_tip.y > ring_pip.y
    pinky_down = pinky_tip.y > pinky_pip.y
    
    return middle_up and index_down and ring_down and pinky_down

def next_video():
    """Focus video player and go to next video"""
    screen_width, screen_height = pyautogui.size()
    pyautogui.click(screen_width//2, screen_height//2)  # player focus
    time.sleep(0.05)
    pyautogui.hotkey('shift', 'n')

def execute_command(command_id):
    if command_id == 1:  # Play/Pause
        pyautogui.press('space')
        return "Play/Pause"
    elif command_id == 2:  # Forward 10s
        pyautogui.press('l')
        return "Forward 10s"
    elif command_id == 3:  # Backward 10s
        pyautogui.press('j')
        return "Backward 10s"
    elif command_id == 4:  # Next Video
        next_video()
        return "Next Video"
    elif command_id == 5:  # Close YouTube
        pyautogui.hotkey('ctrl', 'w')
        return "Close YouTube"
    return None

# Camera setup
cap = cv2.VideoCapture(0)
for i in range(10):
    ret, frame = cap.read()

# Variables
SENSITIVITY = 35
last_command_times = {1:0, 2:0, 3:0, 4:0, 5:0}
COOLDOWN = 0.5
last_command = None

print("YouTube Hand Control Started!")
print("Commands:")
print("- Thumb + Index = Play/Pause")
print("- Thumb + Middle = Forward 10s")
print("- Thumb + Ring = Backward 10s")
print("- Thumb + Pinky = Next Video")
print("- Middle Finger = Close YouTube")
print("Press 'q' to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.flip(frame, 1)
    frame_height, frame_width = frame.shape[:2]
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    current_time = time.time()
    
    # Info panel
    cv2.rectangle(frame, (10,10), (300,60), (0,0,0), -1)
    cv2.putText(frame, f"Sensitivity: {SENSITIVITY}px", (20,30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    cv2.putText(frame, f"Cooldown: {COOLDOWN}s", (20,50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            landmarks = hand_landmarks.landmark
            
            # Middle finger gesture - Close YouTube
            if middle_finger_gesture(landmarks):
                cv2.rectangle(frame, (10, frame_height-60), (250, frame_height-20), (0,0,255), -1)
                cv2.putText(frame, "CLOSE YOUTUBE", (20, frame_height-35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                if current_time - last_command_times[5] > COOLDOWN:
                    result = execute_command(5)
                    if result:
                        last_command_times[5] = current_time
                        last_command = result
                        print(f"Executed: {result}")
                continue
            
            # Finger combinations
            combinations = [
                (INDEX, 1, "Play/Pause"),
                (MIDDLE, 2, "Forward 10s"),
                (RING, 3, "Backward 10s"),
                (PINKY, 4, "Next Video")
            ]
            
            active_commands = []
            for finger_id, command_id, command_name in combinations:
                touching, distance = fingers_touching(landmarks, finger_id, frame_width, frame_height, SENSITIVITY)
                if touching:
                    active_commands.append((command_id, command_name))
                    
                    thumb_x = int(landmarks[THUMB].x * frame_width)
                    thumb_y = int(landmarks[THUMB].y * frame_height)
                    finger_x = int(landmarks[finger_id].x * frame_width)
                    finger_y = int(landmarks[finger_id].y * frame_height)
                    
                    cv2.circle(frame, (thumb_x, thumb_y), 10, (0,255,0), -1)
                    cv2.circle(frame, (finger_x, finger_y), 10, (0,255,0), -1)
                    cv2.line(frame, (thumb_x, thumb_y), (finger_x, finger_y), (0,255,0), 3)
                    
                    mid_x = (thumb_x + finger_x)//2
                    mid_y = (thumb_y + finger_y)//2
                    cv2.putText(frame, f"{distance:.0f}px", (mid_x-15, mid_y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
            
            # Execute single active command
            if len(active_commands) == 1:
                command_id, command_name = active_commands[0]
                if current_time - last_command_times[command_id] > COOLDOWN:
                    result = execute_command(command_id)
                    if result:
                        last_command_times[command_id] = current_time
                        last_command = result
                        print(f"Executed: {result}")
            
            # Status display
            if active_commands:
                if len(active_commands) == 1:
                    _, command_name = active_commands[0]
                    cv2.rectangle(frame, (10, frame_height-60), (250, frame_height-20), (0,255,0), -1)
                    cv2.putText(frame, f"READY: {command_name}", (20, frame_height-35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
                else:
                    cv2.rectangle(frame, (10, frame_height-60), (300, frame_height-20), (0,0,255), -1)
                    cv2.putText(frame, "Multiple commands detected", (20, frame_height-35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
    
    else:
        cv2.putText(frame, "No hand detected", (20, frame_height-20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
    
    # Last command display
    if last_command and current_time - max(last_command_times.values()) < 2:
        cv2.putText(frame, f"Last: {last_command}", (frame_width-200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 2)
    
    # Show frame
    cv2.imshow('YouTube Hand Control', frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('+'):
        SENSITIVITY = min(100, SENSITIVITY+5)
        print(f"Sensitivity: {SENSITIVITY}px")
    elif key == ord('-'):
        SENSITIVITY = max(15, SENSITIVITY-5)
        print(f"Sensitivity: {SENSITIVITY}px")

cap.release()
cv2.destroyAllWindows()
print("Program ended!")
