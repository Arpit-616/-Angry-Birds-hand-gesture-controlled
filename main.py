import cv2
import mediapipe as mp
import math
import pyautogui as pg
import time
import signal
import sys

# Initialize MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Configure PyAutoGUI - DISABLE failsafe and minimize pause
pg.FAILSAFE = False  # Prevent corner triggering
pg.PAUSE = 0.001     # Reduced from 0.005 to minimize sleep time

# Initialize camera with optimized resolution for better performance
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 30)

# Initialize hand tracking with optimized parameters for faster detection
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    static_image_mode=False
)

# Global variables
pinch_position = []
direction = [0, 0]
slope = 0
last_pinch_time = 0
pinch_duration = 0
smoothing_factor = 0.3
gesture_history = []
screen_width, screen_height = pg.size()
is_dragging = False
click_cooldown = 0
gesture_mode = "cursor"
mode_colors = {
    "cursor": (0, 255, 0),
    "scroll": (255, 0, 0),
    "zoom": (0, 0, 255)
}

# Status display settings
font = cv2.FONT_HERSHEY_SIMPLEX
status_color = (255, 255, 255)

# Add safety bounds to prevent cursor from triggering corners
SAFETY_MARGIN = 5  # pixels from screen edge

# Set up signal handler for clean exit
def signal_handler(sig, frame):
    print("\nExiting gracefully...")
    if is_dragging:
        try:
            # Use _pause=False to avoid sleep during interrupt
            pg.mouseUp(_pause=False)
        except:
            pass
    camera.release()
    cv2.destroyAllWindows()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)

def safe_cursor_pos(x, y):
    """Ensure cursor position is within safe bounds"""
    return (
        max(SAFETY_MARGIN, min(screen_width - SAFETY_MARGIN, x)),
        max(SAFETY_MARGIN, min(screen_height - SAFETY_MARGIN, y))
    )

def movecursor(speed_multiplier=1.0):
    """Move cursor with improved responsiveness and smoothing"""
    try:
        x = pg.position().x
        y = pg.position().y
        
        # Calculate movement with smoothing and speed adjustment
        move_x = direction[0] * 10 * speed_multiplier
        
        # Handle slope calculation more robustly
        if abs(slope) > 10:  # Very steep slope
            move_y = direction[1] * 10 * speed_multiplier
        else:
            move_y = direction[1] * abs(slope) * 3 * speed_multiplier
        
        # Apply smoothing
        new_x = x + move_x
        new_y = y + move_y
        
        # Apply safety bounds
        new_x, new_y = safe_cursor_pos(new_x, new_y)
        
        # Move cursor with no delay
        pg.moveTo(new_x, new_y, _pause=False)
    except Exception as e:
        print(f"Error moving cursor: {e}")

def scroll(direction_y):
    """Scroll based on vertical hand movement"""
    try:
        scroll_amount = int(direction_y * abs(slope) * 2)
        pg.scroll(scroll_amount, _pause=False)  # Added _pause=False
    except Exception as e:
        print(f"Error scrolling: {e}")

def zoom(pinch_distance):
    """Zoom in/out based on pinch distance"""
    try:
        if pinch_distance < 30:
            pg.hotkey('ctrl', '-', _pause=False)  # Added _pause=False
        elif pinch_distance > 70:
            pg.hotkey('ctrl', '+', _pause=False)  # Added _pause=False
    except Exception as e:
        print(f"Error zooming: {e}")

def changedirection(pinch_position, currpos):
    """Calculate movement direction with improved precision"""
    global slope, direction
    
    # Calculate x direction with reduced threshold for faster response
    if currpos[0] > pinch_position[0] + 3:
        direction[0] = min((currpos[0] - pinch_position[0]) / 80, 2.0)
    elif currpos[0] < pinch_position[0] - 3:
        direction[0] = max((currpos[0] - pinch_position[0]) / 80, -2.0)
    else:
        direction[0] = 0
    
    # Calculate y direction with reduced threshold
    if currpos[1] > pinch_position[1] + 3:
        direction[1] = min((currpos[1] - pinch_position[1]) / 80, 2.0)
    elif currpos[1] < pinch_position[1] - 3:
        direction[1] = max((currpos[1] - pinch_position[1]) / 80, -2.0)
    else:
        direction[1] = 0
    
    # Calculate slope with error handling
    if abs(currpos[0] - pinch_position[0]) > 3:
        slope = (currpos[1] - pinch_position[1]) / (currpos[0] - pinch_position[0])
        # Limit extreme slopes
        slope = max(-10, min(10, slope))
    else:
        # Default slope for vertical movement
        slope = 10 if currpos[1] > pinch_position[1] else -10

def get_hand_landmarks(landmarks, image):
    """Extract all important hand landmarks"""
    (h, w, c) = image.shape
    results = {}
    
    # Only process essential landmarks for speed
    landmark_indices = {
        "thumb_tip": 4,
        "index_tip": 8,
        "middle_tip": 12,
        "pinky_tip": 20,
        "wrist": 0
    }
    
    for name, index in landmark_indices.items():
        if index < len(landmarks.landmark):
            lm = landmarks.landmark[index]
            results[name] = (int(lm.x * w), int(lm.y * h))
    
    return results

def getcurrentPosition(landmarks, image):
    """Get the current pinch position (midpoint between thumb and index)"""
    hand_points = get_hand_landmarks(landmarks, image)
    
    if "thumb_tip" in hand_points and "index_tip" in hand_points:
        thumb_pos = hand_points["thumb_tip"]
        index_pos = hand_points["index_tip"]
        
        return ((thumb_pos[0] + index_pos[0]) / 2,
                (thumb_pos[1] + index_pos[1]) / 2)
    return None

def detect_gestures(hand_points):
    """Detect various hand gestures"""
    global gesture_mode
    
    if not hand_points or len(hand_points) < 3:
        return None
    
    # Check for mode switch gesture (pinky and thumb extended)
    if "pinky_tip" in hand_points and "thumb_tip" in hand_points and "wrist" in hand_points:
        pinky = hand_points["pinky_tip"]
        thumb = hand_points["thumb_tip"]
        wrist = hand_points["wrist"]
        
        # If pinky and thumb are extended (far from wrist) - reduced threshold
        pinky_extended = math.dist(pinky, wrist) > 120
        thumb_extended = math.dist(thumb, wrist) > 120
        
        if pinky_extended and thumb_extended:
            # Cycle through modes
            modes = list(mode_colors.keys())
            current_index = modes.index(gesture_mode)
            gesture_mode = modes[(current_index + 1) % len(modes)]
            # Use a shorter sleep time and try/except to prevent interrupts
            try:
                time.sleep(0.2)  # Reduced from 0.3
            except KeyboardInterrupt:
                pass
            return "mode_switch"
    
    return None

def isPinch(landmarks, image):
    """Detect pinch gesture with improved accuracy and speed"""
    hand_points = get_hand_landmarks(landmarks, image)
    
    if "thumb_tip" in hand_points and "index_tip" in hand_points:
        thumb_pos = hand_points["thumb_tip"]
        index_pos = hand_points["index_tip"]
        
        # Calculate distance between thumb and index finger
        distance = math.dist(thumb_pos, index_pos)
        
        # Detect pinch gesture with reduced threshold for faster detection
        if distance <= 55:
            global pinch_position, last_pinch_time, pinch_duration
            
            # Record pinch start time for duration tracking
            current_time = time.time()
            if len(pinch_position) == 0:
                last_pinch_time = current_time
                pinch_position = ((thumb_pos[0] + index_pos[0]) / 2,
                                 (thumb_pos[1] + index_pos[1]) / 2)
            
            # Update pinch duration
            pinch_duration = current_time - last_pinch_time
            
            return True, distance
        else:
            return False, distance
    else:
        return False, 0

def draw_status(image, text, position=(30, 30), color=(255, 255, 255)):
    """Draw status text on the image"""
    cv2.putText(image, text, position, font, 0.7, color, 2, cv2.LINE_AA)

# Main loop
last_frame_time = time.time()
frame_count = 0
fps = 0

try:
    while True:
        # Calculate FPS
        current_time = time.time()
        frame_count += 1
        if current_time - last_frame_time >= 1.0:
            fps = frame_count
            frame_count = 0
            last_frame_time = current_time
        
        # Capture frame
        ret, image = camera.read()
        if not ret:
            print("Failed to capture image from camera")
            continue
        
        # Process image - use smaller image for faster processing
        image = cv2.flip(image, 1)  # Mirror image for more intuitive control
        
        # Convert to RGB for MediaPipe
        cimg = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(cimg)
        
        # Draw mode and status information
        draw_status(image, f"Mode: {gesture_mode.upper()}", (30, 30), mode_colors[gesture_mode])
        draw_status(image, f"FPS: {fps}", (30, 60))
        
        if click_cooldown > 0:
            click_cooldown -= 1
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Check for pinch - do this first for faster response
                is_pinching, pinch_distance = isPinch(hand_landmarks, image)
                
                if is_pinching:
                    # Draw pinch indicator
                    cv2.circle(image, (50, 100), 20, (0, 255, 0), -1)
                    draw_status(image, f"Pinch: {pinch_duration:.1f}s", (30, 90), (0, 255, 0))
                    
                    # Get current position
                    currpos = getcurrentPosition(hand_landmarks, image)
                    
                    if currpos and pinch_position:
                        # Calculate direction
                        changedirection(pinch_position, currpos)
                        
                        # Perform action based on mode
                        if gesture_mode == "cursor":
                            # Long pinch = drag, short pinch = click
                            if pinch_duration > 0.3 and not is_dragging:
                                is_dragging = True
                                try:
                                    pg.mouseDown(_pause=False)  # Added _pause=False
                                except Exception as e:
                                    print(f"Error in mouseDown: {e}")
                            
                            # Move cursor with speed based on pinch duration
                            speed_multiplier = min(1.8, 1.0 + pinch_duration / 5)
                            movecursor(speed_multiplier)
                        
                        elif gesture_mode == "scroll":
                            scroll(direction[1])
                        
                        elif gesture_mode == "zoom":
                            zoom(pinch_distance)
                            
                    # Check for gestures after handling pinch
                    hand_points = get_hand_landmarks(hand_landmarks, image)
                    detect_gestures(hand_points)
                else:
                    # Draw pinch indicator (off)
                    cv2.circle(image, (50, 100), 20, (0, 0, 255), -1)
                    
                    # Handle end of pinch
                    if is_dragging:
                        try:
                            pg.mouseUp(_pause=False)  # Added _pause=False to prevent sleep
                        except Exception as e:
                            print(f"Error in mouseUp: {e}")
                        is_dragging = False
                    
                    # Check for quick pinch (click) - reduced duration for faster clicks
                    if pinch_duration > 0.05 and pinch_duration < 0.3 and click_cooldown == 0 and gesture_mode == "cursor":
                        try:
                            pg.click(_pause=False)  # Added _pause=False
                        except Exception as e:
                            print(f"Error clicking: {e}")
                        click_cooldown = 5
                    
                    # Reset pinch tracking
                    direction = [0, 0]
                    pinch_position = []
                    pinch_duration = 0
        
        # Show image - use a smaller window for better performance
        cv2.imshow('Hand Gesture Control', image)
        
        # Check for exit - use ESC key as alternative
        key = cv2.waitKey(1) 
        if key == ord('q') or key == 27:  # q or ESC
            break

except KeyboardInterrupt:
    print("\nProgram interrupted by user")
except Exception as e:
    print(f"\nError: {e}")
finally:
    # Cleanup - this will always execute even if interrupted
    print("Cleaning up resources...")
    try:
        # Make sure mouse is released if program exits during drag
        if is_dragging:
            pg.mouseUp(_pause=False)  # Added _pause=False
        camera.release()
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"Error during cleanup: {e}")
    