# ✋🎨 Air Canvas Pro v4  

Gesture-first infinite canvas powered by OpenCV + MediaPipe Hands.  
Draw, erase, pan, undo, redo, and control tools using only hand gestures.

---

## 🚀 Overview

Air Canvas Pro v4 is a real-time computer vision drawing application that transforms your webcam into a gesture-controlled canvas.

### Key Features

- Infinite panning canvas  
- Multi-hand gesture recognition  
- Sidebar UI controlled via hover + pinch  
- Smooth brush & opacity control  
- Undo / Redo with swipe gestures  
- Fist-hold clear with visual progress indicator  
- Two-hand dynamic brush sizing  
- Opacity blending  
- Shape drawing tools  

Built using:

- Python  
- OpenCV  
- NumPy  
- MediaPipe Hands  

---

## 🖐 Gesture System

| Gesture | Action |
|----------|--------|
| 👉 Index finger + Pinch | Draw |
| ✌ Index + Middle + Pinch | Erase |
| ✋ Open palm + Pinch | Pan |
| ✋ Open palm + Swipe Left | Undo |
| ✋ Open palm + Swipe Right | Redo |
| ✊ Fist (hold 2 sec) | Clear canvas |
| 🙌 Two hands (spread/squeeze index fingers) | Brush size control |
| Hover + Pinch on sidebar | Click UI |
| Keyboard `S` | Save |

---

## 🧠 Gesture Design Principles

To prevent accidental triggers:

- Pinch exclusively triggers drawing actions  
- Tool switching only works when NOT pinching  
- Undo/Redo requires full open palm + velocity threshold  
- Clear requires deliberate 2-second fist hold  
- Save is restricted to sidebar or keyboard  

This ensures stable real-time performance.

---

## 🎛 Sidebar Features

Located on the right edge of the screen.

Includes:

- 🎨 Color palette  
- 🖊 Tool selection (Draw, Erase, Line, Rect, Circle, Triangle, Arrow, Pan)  
- 🧵 Brush size slider  
- 🌫 Opacity slider  
- 🟢 Fill toggle  
- ↩ Undo  
- ↪ Redo  
- 🗑 Clear  
- 💾 Save  

### Interaction

- Hover over item  
- Pinch to click  

---

## 🧰 Tools

| Tool | Description |
|------|-------------|
| Draw | Freehand drawing |
| Erase | Erases using black stroke |
| Line | Straight line |
| Rect | Rectangle |
| Circle | Circle |
| Triangle | Triangle |
| Arrow | Arrow line |
| Pan | Move across infinite canvas |

---

## 🖥 Infinite Canvas

- Canvas size = 3x screen resolution  
- Scrollable via pan gesture  
- Edge indicators displayed  
- Fully undo/redo supported  
- Canvas composited using OpenCV blending  

---

## ⌨ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `[` / `]` | Decrease / Increase brush |
| `z` | Undo |
| `y` | Redo |
| `c` | Clear |
| `f` | Toggle fill |
| `p` | Toggle pan mode |
| `q` | Quit |

---

## 📦 Installation

### 1️⃣ Clone Repository

```bash
git clone <your-repo-url>
cd air-canvas-pro
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
```

### 3️⃣ Install Dependencies

```bash
pip install opencv-python mediapipe numpy
```

---

## ▶ Run Application

```bash
python air_canvas.py
```

### Ensure

- Webcam is connected  
- Good lighting conditions  
- Hand fully visible in frame  

---

## 🏗 Architecture Overview

### Core Modules

#### 1. Hand Detection
- MediaPipe Hands  
- Landmark tracking  
- Multi-hand support  

#### 2. Gesture Recognition Layer
- Finger state detection  
- Pinch smoothing buffer  
- Swipe velocity detection  
- Fist hold timer  
- Tool auto-switch logic  

#### 3. Canvas Engine
- Infinite canvas buffer  
- Pan offset tracking  
- Undo/Redo stack  
- Opacity blending via `addWeighted`  

#### 4. Sidebar Renderer
- Rounded button UI  
- Sliders  
- Glass panel design  
- Hover detection  

#### 5. Gesture UI Overlay
- Hint banner  
- Circular hold-progress indicator  

---

## 🔄 Undo / Redo System

- Stack-based (max 20 states)  
- Redo cleared on new action  
- Swipe cooldown prevents double-trigger  
- Snapshot stored only at action start  

---

## 🧪 Stability Safeguards

- Gesture cooldown system  
- Swipe velocity threshold  
- Pinch smoothing buffer  
- Cursor smoothing (mean filter)  
- Clear confirmation via hold gesture  
- Tool switching restricted to canvas zone  

---

## 🎯 Performance Tips

- Use bright, even lighting  
- Avoid cluttered backgrounds  
- Keep hand fully visible  
- Avoid overlapping hands unless resizing brush  
- Use moderate brush sizes for smoother drawing  

---

## 📁 Output

Saved files format:

```
air_canvas_<timestamp>.png
```

Stored in project directory.

---

## 🛠 Future Improvements

- Pressure simulation  
- Multi-layer canvas  
- Shape rotation gesture  
- AI shape correction  
- Save to PDF  
- Export as SVG  
- Gesture customization  
- Multiplayer collaborative mode  

---

## 📚 Requirements

- Python 3.9+  
- OpenCV  
- NumPy  
- MediaPipe  
- Webcam  

---

## 👨‍💻 Author

Air Canvas Pro v4  
Gesture-first UX drawing system  
