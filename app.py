import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
import io
import base64
from datetime import datetime
import time

# Page config
st.set_page_config(
    page_title="Hand Tracking Whiteboard ✋",
    page_icon="🖐️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .sidebar-content {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
    }
    .info-box {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .status-drawing {
        background: #4CAF50;
        color: white;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
    }
    .status-paused {
        background: #f44336;
        color: white;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
    }
    .status-idle {
        background: #ff9800;
        color: white;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'drawing' not in st.session_state:
    st.session_state.drawing = None
if 'canvas_size' not in st.session_state:
    st.session_state.canvas_size = (800, 500)
if 'color' not in st.session_state:
    st.session_state.color = "#FF0000"
if 'brush_size' not in st.session_state:
    st.session_state.brush_size = 8
if 'history' not in st.session_state:
    st.session_state.history = []
if 'redo_stack' not in st.session_state:
    st.session_state.redo_stack = []
if 'bg_color' not in st.session_state:
    st.session_state.bg_color = "#FFFFFF"
if 'last_point' not in st.session_state:
    st.session_state.last_point = None
if 'is_drawing' not in st.session_state:
    st.session_state.is_drawing = False
if 'points' not in st.session_state:
    st.session_state.points = []
if 'hand_positions' not in st.session_state:
    st.session_state.hand_positions = []

def create_canvas():
    """Create a blank white canvas"""
    return Image.new('RGB', st.session_state.canvas_size, st.session_state.bg_color)

def save_state():
    """Save current state to history"""
    if st.session_state.drawing is not None:
        img_bytes = io.BytesIO()
        st.session_state.drawing.save(img_bytes, format='PNG')
        st.session_state.history.append(img_bytes.getvalue())
        st.session_state.redo_stack = []

def undo():
    """Undo last action"""
    if len(st.session_state.history) > 0:
        st.session_state.redo_stack.append(st.session_state.history.pop())
        if st.session_state.history:
            img = Image.open(io.BytesIO(st.session_state.history[-1]))
            st.session_state.drawing = img
        else:
            st.session_state.drawing = create_canvas()

def redo():
    """Redo last undone action"""
    if st.session_state.redo_stack:
        img_bytes = st.session_state.redo_stack.pop()
        img = Image.open(io.BytesIO(img_bytes))
        st.session_state.drawing = img
        save_state()

def clear_canvas():
    """Clear the canvas"""
    st.session_state.drawing = create_canvas()
    st.session_state.history = []
    st.session_state.redo_stack = []
    st.session_state.points = []
    st.session_state.hand_positions = []
    st.session_state.last_point = None

def draw_line(canvas, point1, point2, color, size):
    """Draw a line between two points"""
    if point1 is None or point2 is None:
        return canvas
    
    draw = ImageDraw.Draw(canvas)
    draw.line([point1, point2], fill=color, width=size)
    return canvas

# Initialize canvas
if st.session_state.drawing is None:
    st.session_state.drawing = create_canvas()

# Header
st.markdown('<div class="main-header"><h1>🖐️ Hand Tracking Whiteboard</h1><p>Draw in the air using your finger! Use the camera to track your hand.</p></div>', unsafe_allow_html=True)

# Main layout
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown('<div class="info-box">🎥 <b>Camera Required:</b> Click "Start Drawing" below and allow camera access. Show your hand to start drawing!</div>', unsafe_allow_html=True)
    
    # Display canvas
    canvas_container = st.empty()
    canvas_container.image(st.session_state.drawing, use_container_width=True)
    
    # Status display
    status_container = st.empty()
    
    # Camera input
    st.markdown("### 🎥 Camera Controls")
    
    col_cam1, col_cam2, col_cam3 = st.columns(3)
    
    with col_cam1:
        start_camera = st.button("🎥 Start Drawing", use_container_width=True, type="primary")
    
    with col_cam2:
        stop_camera = st.button("⏹️ Stop Drawing", use_container_width=True)
    
    with col_cam3:
        clear_btn = st.button("🗑️ Clear Canvas", use_container_width=True)
        if clear_btn:
            clear_canvas()
            st.rerun()
    
    if start_camera:
        st.session_state.is_drawing = True
        status_container.markdown('<div class="status-drawing">🎨 Drawing Mode Active - Show your hand!</div>', unsafe_allow_html=True)
    
    if stop_camera:
        st.session_state.is_drawing = False
        status_container.markdown('<div class="status-paused">⏸️ Drawing Paused</div>', unsafe_allow_html=True)
    
    # Camera input for hand tracking
    if st.session_state.is_drawing:
        # Use camera input
        camera_image = st.camera_input("📸 Position your hand in front of the camera")
        
        if camera_image is not None:
            # Process the image
            try:
                # Convert to PIL Image
                img = Image.open(camera_image)
                
                # Convert to numpy array
                import cv2
                import mediapipe as mp
                
                # Convert PIL to numpy
                img_np = np.array(img)
                
                # Flip horizontally for natural movement
                img_np = cv2.flip(img_np, 1)
                
                # Initialize MediaPipe
                mp_hands = mp.solutions.hands
                hands = mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=1,
                    min_detection_confidence=0.7,
                    min_tracking_confidence=0.5
                )
                mp_draw = mp.solutions.drawing_utils
                
                # Convert to RGB
                rgb_img = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb_img)
                
                # Create display image
                display_img = img_np.copy()
                
                if results.multi_hand_landmarks:
                    # Get first hand
                    landmarks = results.multi_hand_landmarks[0]
                    
                    # Draw hand landmarks
                    mp_draw.draw_landmarks(
                        display_img,
                        landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2),
                        mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )
                    
                    # Get index finger tip (landmark 8)
                    h, w, _ = img_np.shape
                    index_tip = landmarks.landmark[8]
                    finger_x = int(index_tip.x * w)
                    finger_y = int(index_tip.y * h)
                    
                    # Check if fist (all fingertips below joints)
                    tips = [8, 12, 16, 20]  # Index, middle, ring, pinky tips
                    joints = [6, 10, 14, 18]  # Corresponding joints
                    
                    finger_folded = 0
                    for tip_idx, joint_idx in zip(tips, joints):
                        tip = landmarks.landmark[tip_idx]
                        joint = landmarks.landmark[joint_idx]
                        if tip.y > joint.y:
                            finger_folded += 1
                    
                    is_fist = finger_folded >= 3
                    
                    # Map to canvas coordinates
                    canvas_w, canvas_h = st.session_state.canvas_size
                    canvas_x = int((finger_x / w) * canvas_w)
                    canvas_y = int((finger_y / h) * canvas_h)
                    
                    # Ensure within bounds
                    canvas_x = max(0, min(canvas_x, canvas_w - 1))
                    canvas_y = max(0, min(canvas_y, canvas_h - 1))
                    
                    current_point = (canvas_x, canvas_y)
                    
                    # Draw or pause
                    if is_fist:
                        status_container.markdown('<div class="status-paused">✊ Fist detected - Drawing paused</div>', unsafe_allow_html=True)
                        st.session_state.last_point = None
                        cv2.putText(display_img, "✊ PAUSED", (10, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    else:
                        status_container.markdown('<div class="status-drawing">☝️ Drawing - Move your finger!</div>', unsafe_allow_html=True)
                        
                        # Draw on canvas
                        if st.session_state.last_point is not None:
                            st.session_state.drawing = draw_line(
                                st.session_state.drawing,
                                st.session_state.last_point,
                                current_point,
                                st.session_state.color,
                                st.session_state.brush_size
                            )
                            # Update canvas display
                            canvas_container.image(st.session_state.drawing, use_container_width=True)
                        
                        st.session_state.last_point = current_point
                        
                        # Draw circle at finger tip
                        cv2.circle(display_img, (finger_x, finger_y), 10, (0, 255, 255), -1)
                        cv2.putText(display_img, "☝️ DRAWING", (10, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    status_container.markdown('<div class="status-idle">👋 No hand detected - Show your hand</div>', unsafe_allow_html=True)
                    st.session_state.last_point = None
                
                # Display the camera feed
                display_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
                st.image(display_rgb, use_container_width=True, caption="Camera Feed - Hand Tracking")
                
                # Save state periodically
                if len(st.session_state.history) > 0 and len(st.session_state.history) % 10 == 0:
                    save_state()
                
                # Release resources
                hands.close()
                
            except ImportError as e:
                st.error("⚠️ OpenCV or MediaPipe not installed. Installing now...")
                st.info("Please wait a moment and refresh the page.")
            except Exception as e:
                st.error(f"Error processing image: {str(e)}")

with col2:
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    
    # Drawing tools
    st.subheader("🎨 Tools")
    
    # Color picker
    st.session_state.color = st.color_picker("Color", st.session_state.color)
    
    # Brush size
    st.session_state.brush_size = st.slider("Brush Size", 2, 30, st.session_state.brush_size, step=2)
    
    st.markdown("---")
    
    # Actions
    st.subheader("⚡ Actions")
    
    col_undo, col_redo = st.columns(2)
    with col_undo:
        if st.button("↩️ Undo", use_container_width=True):
            undo()
            st.rerun()
    with col_redo:
        if st.button("↪️ Redo", use_container_width=True):
            redo()
            st.rerun()
    
    st.markdown("---")
    
    # Background
    st.subheader("🖼️ Background")
    st.session_state.bg_color = st.color_picker("Background Color", st.session_state.bg_color)
    if st.button("Apply Background", use_container_width=True):
        current_drawing = st.session_state.drawing
        new_canvas = Image.new('RGB', st.session_state.canvas_size, st.session_state.bg_color)
        new_canvas.paste(current_drawing, (0, 0))
        st.session_state.drawing = new_canvas
        st.rerun()
    
    st.markdown("---")
    
    # Export
    st.subheader("💾 Export")
    
    if st.button("📥 Download PNG", use_container_width=True):
        if st.session_state.drawing:
            img_bytes = io.BytesIO()
            st.session_state.drawing.save(img_bytes, format='PNG')
            b64 = base64.b64encode(img_bytes.getvalue()).decode()
            href = f'<a href="data:image/png;base64,{b64}" download="hand_drawing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png">📥 Click to Download</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Info
    st.subheader("📊 Info")
    st.caption(f"Points in History: {len(st.session_state.history)}")
    st.caption(f"Canvas Size: {st.session_state.canvas_size[0]}x{st.session_state.canvas_size[1]}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Help section
with st.expander("❓ How to use Hand Tracking Whiteboard"):
    st.markdown("""
    ### 🎯 How it works
    1. Click **"Start Drawing"** to activate camera
    2. **Allow camera access** when prompted
    3. Show your hand in front of the camera
    4. Extend your **index finger** to draw
    5. Make a **fist** to pause drawing
    6. Use sidebar to change colors and brush size
    
    ### 🖐️ Gestures
    - **Index Finger Up**: Drawing mode ☝️
    - **Fist**: Drawing paused ✊
    - **No Hand**: Idle mode 👋
    
    ### 💡 Tips for Best Results
    - **Good Lighting**: Ensure your hand is well-lit
    - **Clear Background**: Avoid busy backgrounds
    - **Steady Hand**: Move slowly for precise drawings
    - **Camera Position**: Place camera at eye level
    
    ### ⚠️ Troubleshooting
    - If camera doesn't work, check browser permissions
    - If tracking is jittery, improve lighting
    - Refresh page if tracking stops
    - First load may take a few seconds
    """)

st.markdown("---")
st.caption("Made with ❤️ using Streamlit, OpenCV, and MediaPipe")
