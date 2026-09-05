import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import base64
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Hand Tracking Whiteboard ✋",
    page_icon="🖐️",
    layout="wide"
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
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'canvas' not in st.session_state:
    st.session_state.canvas = None
if 'color' not in st.session_state:
    st.session_state.color = (255, 0, 0)
if 'brush_size' not in st.session_state:
    st.session_state.brush_size = 5
if 'drawing' not in st.session_state:
    st.session_state.drawing = False
if 'last_point' not in st.session_state:
    st.session_state.last_point = None

def create_canvas():
    return np.ones((480, 640, 3), dtype=np.uint8) * 255

# Initialize canvas
if st.session_state.canvas is None:
    st.session_state.canvas = create_canvas()

# Header
st.markdown('<div class="main-header"><h1>🖐️ Hand Tracking Whiteboard</h1></div>', unsafe_allow_html=True)

# Layout
col1, col2 = st.columns([2, 1])

with col1:
    # Camera feed
    camera_placeholder = st.empty()
    canvas_placeholder = st.empty()
    
    # Show canvas
    canvas_placeholder.image(st.session_state.canvas, channels="BGR", use_container_width=True)
    
    # Start/Stop buttons
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        start_btn = st.button("🎥 Start Camera", type="primary")
    with col_btn2:
        stop_btn = st.button("⏹️ Stop")
    with col_btn3:
        clear_btn = st.button("🗑️ Clear")
        if clear_btn:
            st.session_state.canvas = create_canvas()
            st.session_state.last_point = None
            st.rerun()

    if start_btn:
        st.session_state.drawing = True
        
        # Open camera
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Import MediaPipe
        import mediapipe as mp
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        mp_draw = mp.solutions.drawing_utils
        
        status_placeholder = st.empty()
        
        while st.session_state.drawing:
            ret, frame = cap.read()
            if not ret:
                st.error("Camera error")
                break
            
            # Flip frame
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            
            # Draw hand landmarks
            display_frame = frame.copy()
            
            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(
                    display_frame,
                    landmarks,
                    mp_hands.HAND_CONNECTIONS
                )
                
                # Get index finger tip
                h, w, _ = frame.shape
                index_tip = landmarks.landmark[8]
                x = int(index_tip.x * w)
                y = int(index_tip.y * h)
                
                # Check if fist
                tips = [8, 12, 16, 20]
                joints = [6, 10, 14, 18]
                folded = 0
                for tip_idx, joint_idx in zip(tips, joints):
                    tip = landmarks.landmark[tip_idx]
                    joint = landmarks.landmark[joint_idx]
                    if tip.y > joint.y:
                        folded += 1
                
                is_fist = folded >= 3
                
                # Map to canvas
                canvas_h, canvas_w = st.session_state.canvas.shape[:2]
                canvas_x = int((x / w) * canvas_w)
                canvas_y = int((y / h) * canvas_h)
                
                # Draw or pause
                if is_fist:
                    status_placeholder.warning("✊ PAUSED - Make a fist to stop drawing")
                    st.session_state.last_point = None
                    cv2.circle(display_frame, (x, y), 10, (0, 0, 255), -1)
                else:
                    status_placeholder.success("☝️ DRAWING - Move your finger")
                    current_point = (canvas_x, canvas_y)
                    
                    if st.session_state.last_point is not None:
                        # Draw on canvas
                        cv2.line(
                            st.session_state.canvas,
                            st.session_state.last_point,
                            current_point,
                            st.session_state.color,
                            st.session_state.brush_size
                        )
                    
                    st.session_state.last_point = current_point
                    cv2.circle(display_frame, (x, y), 10, (0, 255, 255), -1)
                    
                    # Update canvas display
                    canvas_placeholder.image(st.session_state.canvas, channels="BGR", use_container_width=True)
            else:
                status_placeholder.info("👋 Show your hand to the camera")
                st.session_state.last_point = None
            
            # Show camera feed
            camera_placeholder.image(display_frame, channels="BGR", use_container_width=True)
        
        cap.release()
        hands.close()
        cv2.destroyAllWindows()
        st.session_state.drawing = False

    if stop_btn:
        st.session_state.drawing = False
        st.rerun()

with col2:
    st.subheader("🎨 Tools")
    
    # Color picker
    color_hex = st.color_picker("Color", "#FF0000")
    color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (1, 3, 5))
    st.session_state.color = (color_rgb[2], color_rgb[1], color_rgb[0])  # BGR
    
    # Brush size
    st.session_state.brush_size = st.slider("Size", 2, 20, 5)
    
    st.markdown("---")
    
    # Download
    if st.button("💾 Download"):
        if st.session_state.canvas is not None:
            img = Image.fromarray(st.session_state.canvas)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            b64 = base64.b64encode(img_bytes.getvalue()).decode()
            href = f'<a href="data:image/png;base64,{b64}" download="drawing.png">Click to Download</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("☝️ Index finger = Draw")
    st.caption("✊ Fist = Pause")
    st.caption("👋 No hand = Idle")
