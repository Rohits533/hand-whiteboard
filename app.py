import streamlit as st
import cv2
import numpy as np
from PIL import Image
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
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'drawing' not in st.session_state:
    st.session_state.drawing = None
if 'canvas_size' not in st.session_state:
    st.session_state.canvas_size = (800, 600)
if 'color' not in st.session_state:
    st.session_state.color = "#FF0000"
if 'brush_size' not in st.session_state:
    st.session_state.brush_size = 8
if 'history' not in st.session_state:
    st.session_state.history = []
if 'redo_stack' not in st.session_state:
    st.session_state.redo_stack = []
if 'is_drawing' not in st.session_state:
    st.session_state.is_drawing = False
if 'last_point' not in st.session_state:
    st.session_state.last_point = None
if 'drawing_enabled' not in st.session_state:
    st.session_state.drawing_enabled = True

def create_canvas():
    """Create blank canvas"""
    return np.ones((st.session_state.canvas_size[1], st.session_state.canvas_size[0], 3), dtype=np.uint8) * 255

def save_state():
    """Save current state to history"""
    if st.session_state.drawing is not None:
        img = Image.fromarray(st.session_state.drawing)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        st.session_state.history.append(img_bytes.getvalue())
        st.session_state.redo_stack = []

def undo():
    """Undo last action"""
    if len(st.session_state.history) > 0:
        st.session_state.redo_stack.append(st.session_state.history.pop())
        if st.session_state.history:
            img = Image.open(io.BytesIO(st.session_state.history[-1]))
            st.session_state.drawing = np.array(img)
        else:
            st.session_state.drawing = create_canvas()

def redo():
    """Redo last undone action"""
    if st.session_state.redo_stack:
        img_bytes = st.session_state.redo_stack.pop()
        img = Image.open(io.BytesIO(img_bytes))
        st.session_state.drawing = np.array(img)
        save_state()

def clear_canvas():
    """Clear the canvas"""
    st.session_state.drawing = create_canvas()
    st.session_state.history = []
    st.session_state.redo_stack = []
    st.session_state.last_point = None

def draw_on_canvas(canvas, point1, point2, color, size):
    """Draw line between two points"""
    if point1 is None or point2 is None:
        return canvas
    
    color_hex = color.lstrip('#')
    color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
    color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])
    
    cv2.line(canvas, point1, point2, color_bgr, size)
    return canvas

# Initialize canvas
if st.session_state.drawing is None:
    st.session_state.drawing = create_canvas()

# Header
st.markdown('<div class="main-header"><h1>🖐️ Hand Tracking Whiteboard</h1><p>Draw in the air using your finger! Move your index finger to create art.</p></div>', unsafe_allow_html=True)

# Main layout
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown('<div class="info-box">🎥 <b>Camera Required:</b> Please allow camera access when prompted. Show your hand to start drawing!</div>', unsafe_allow_html=True)
    
    # Video feed
    frame_placeholder = st.empty()
    canvas_placeholder = st.empty()
    
    # Camera control
    run = st.checkbox('🎥 Start Camera', value=True)
    
    if run:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Instructions
        st.info("""
        **✋ Instructions:** 
        - Show your **index finger** to draw 
        - Make a **fist** to stop drawing
        - Move your finger to create art!
        """)
        
        # Status display
        status_placeholder = st.empty()
        
        # Import hand tracker
        try:
            from utils.hand_tracker import HandTracker
            hand_tracker = HandTracker()
            
            while run:
                ret, frame = cap.read()
                if not ret:
                    st.error("Failed to access camera")
                    break
                
                # Flip frame horizontally
                frame = cv2.flip(frame, 1)
                
                # Track hand
                processed_frame, finger_tip, is_fist = hand_tracker.process_frame(frame)
                
                # Update drawing status
                if is_fist:
                    st.session_state.is_drawing = False
                    st.session_state.last_point = None
                    status_placeholder.info("✊ Fist detected - Drawing paused")
                elif finger_tip is not None:
                    st.session_state.is_drawing = True
                    status_placeholder.success("☝️ Drawing mode - Move your finger!")
                    
                    # Map coordinates to canvas
                    h, w, _ = processed_frame.shape
                    canvas_h, canvas_w = st.session_state.drawing.shape[:2]
                    
                    x = int((finger_tip[0] / w) * canvas_w)
                    y = int((finger_tip[1] / h) * canvas_h)
                    
                    x = max(0, min(x, canvas_w - 1))
                    y = max(0, min(y, canvas_h - 1))
                    
                    current_point = (x, y)
                    
                    if st.session_state.last_point is not None and st.session_state.drawing_enabled:
                        st.session_state.drawing = draw_on_canvas(
                            st.session_state.drawing,
                            st.session_state.last_point,
                            current_point,
                            st.session_state.color,
                            st.session_state.brush_size
                        )
                    
                    st.session_state.last_point = current_point
                else:
                    st.session_state.is_drawing = False
                    st.session_state.last_point = None
                    status_placeholder.warning("👋 No hand detected - Show your hand")
                
                # Display canvas
                canvas_rgb = cv2.cvtColor(st.session_state.drawing, cv2.COLOR_BGR2RGB)
                canvas_placeholder.image(canvas_rgb, channels="RGB", use_container_width=True)
                
                # Display video
                processed_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                frame_placeholder.image(processed_rgb, channels="RGB", use_container_width=True)
                
                time.sleep(0.03)
                
            cap.release()
            cv2.destroyAllWindows()
            
        except ImportError:
            st.error("⚠️ Hand tracker module not found. Please ensure utils/hand_tracker.py exists.")
            st.info("For now, you can use the mouse to draw.")
            
            # Fallback: mouse drawing
            col_draw, col_clear = st.columns(2)
            with col_draw:
                if st.button("✏️ Add Test Drawing"):
                    # Add a simple shape for demo
                    draw = ImageDraw.Draw(Image.fromarray(st.session_state.drawing))
                    for i in range(10):
                        x = 100 + i * 20
                        y = 200 + np.sin(i/2) * 30
                        cv2.circle(st.session_state.drawing, (int(x), int(y)), 5, (255, 0, 0), -1)
                    st.rerun()
            with col_clear:
                if st.button("🗑️ Clear"):
                    clear_canvas()
                    st.rerun()

with col2:
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    
    # Drawing tools
    st.subheader("🎨 Tools")
    
    st.session_state.color = st.color_picker("Color", st.session_state.color)
    st.session_state.brush_size = st.slider("Brush Size", 2, 30, st.session_state.brush_size, step=2)
    st.session_state.drawing_enabled = st.checkbox("✏️ Enable Drawing", value=st.session_state.drawing_enabled)
    
    st.markdown("---")
    
    # Actions
    st.subheader("⚡ Actions")
    
    col_undo, col_redo = st.columns(2)
    with col_undo:
        if st.button("↩️ Undo"):
            undo()
            st.rerun()
    with col_redo:
        if st.button("↪️ Redo"):
            redo()
            st.rerun()
    
    if st.button("🗑️ Clear All"):
        clear_canvas()
        st.rerun()
    
    st.markdown("---")
    
    # Export
    st.subheader("💾 Export")
    
    if st.button("📥 Download PNG"):
        if st.session_state.drawing is not None:
            img = Image.fromarray(cv2.cvtColor(st.session_state.drawing, cv2.COLOR_BGR2RGB))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            b64 = base64.b64encode(img_bytes.getvalue()).decode()
            href = f'<a href="data:image/png;base64,{b64}" download="hand_drawing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png">📥 Click to Download</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Info
    st.subheader("📊 Info")
    st.caption(f"Points: {len(st.session_state.history)}")
    st.caption(f"Canvas: {st.session_state.canvas_size[0]}x{st.session_state.canvas_size[1]}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Help section
with st.expander("❓ How to use Hand Tracking Whiteboard"):
    st.markdown("""
    ### 🎯 How it works
    1. **Start Camera**: Check the box to activate webcam
    2. **Show Your Hand**: Place your hand in front of the camera
    3. **Draw**: Extend your index finger and move it around
    4. **Stop Drawing**: Make a fist to pause drawing
    5. **Change Color**: Use the color picker in sidebar
    
    ### 💡 Tips
    - Good lighting improves tracking
    - Keep hand 1-3 feet from camera
    - Move slowly for precise drawings
    
    ### 🖐️ Gestures
    - **Index Finger Up**: Drawing mode 🖕
    - **Fist**: Drawing paused ✊
    - **All Fingers**: Just browsing 👋
    """)

st.markdown("---")
st.caption("Made with ❤️ using Streamlit, OpenCV, and MediaPipe")
