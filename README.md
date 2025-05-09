# 🎮 AngryGestureBirds - Hand Gesture Controlled Game Interface

Control your computer and games (like Angry Birds) with intuitive hand gestures using your webcam! This project leverages **MediaPipe** for real-time hand tracking and **PyAutoGUI** for system interaction.

## ✨ Features

- 🖱️ **Cursor Mode** – Move, click, and drag using pinch gestures.
- 🖱️ **Scroll Mode** – Scroll vertically using hand motion.
- 🔍 **Zoom Mode** – Zoom in and out with pinch distance.
- 🔄 **Gesture Mode Switching** – Switch between control modes using a pinky + thumb gesture.
- 🔋 **Optimized for Performance** – Fast processing, low latency, and responsive control.

## 📦 Dependencies

Install dependencies via pip:

```bash
pip install opencv-python mediapipe pyautogui
````

> Note: `pyautogui` may require additional permissions for full functionality on some OSes (e.g., macOS accessibility permissions).

## 🚀 Getting Started

Run the script:

```bash
python hand_gesture_controller.py
```

## 🖐️ Controls & Gestures

| Gesture                      | Action                                        |
| ---------------------------- | --------------------------------------------- |
| **Pinch (thumb + index)**    | Activate cursor/scroll/zoom depending on mode |
| **Hold pinch > 0.3s**        | Start drag                                    |
| **Quick pinch (0.05s–0.3s)** | Click (cursor mode only)                      |
| **Move hand while pinched**  | Move cursor / Scroll                          |
| **Pinky + Thumb extended**   | Switch modes (cursor → scroll → zoom → …)     |
| **Pinch distance < 30px**    | Zoom Out                                      |
| **Pinch distance > 70px**    | Zoom In                                       |

## 🧠 Tech Stack

* **MediaPipe** – Real-time hand tracking
* **OpenCV** – Webcam input & display
* **PyAutoGUI** – System interaction (mouse, scroll, keys)
* **Python 3**

## 🛑 Exit

Press `q` or `ESC` to quit the application, or use `Ctrl+C`.

## ⚠️ Safety Features

* Safety bounds prevent cursor from hitting screen corners (avoids system edge triggers).
* Handles drag interruption cleanly on exit or error.

## 📷 Screenshots

> Add screenshots of gesture detection and mode overlays for better illustration.

## 🧩 TODO / Ideas

* Add Angry Birds integration or AI slingshot control
* Multi-hand support
* Voice command mode switching
* Smoother cursor control with Kalman filtering

## 📄 License

MIT License. Free to use and modify.
