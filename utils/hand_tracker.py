import cv2
import mediapipe as mp

class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
    def process_frame(self, frame):
        """Process frame and detect hand landmarks"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        finger_tip = None
        is_fist = False
        processed_frame = frame.copy()
        
        if results.multi_hand_landmarks:
            landmarks = results.multi_hand_landmarks[0]
            
            self.mp_draw.draw_landmarks(
                processed_frame,
                landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2),
                self.mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
            )
            
            h, w, _ = frame.shape
            
            # Index finger tip (landmark 8)
            index_tip = landmarks.landmark[8]
            finger_tip = (int(index_tip.x * w), int(index_tip.y * h))
            
            # Check if fist
            tips = [8, 12, 16, 20]
            joints = [6, 10, 14, 18]
            
            finger_folded = 0
            for tip_idx, joint_idx in zip(tips, joints):
                tip = landmarks.landmark[tip_idx]
                joint = landmarks.landmark[joint_idx]
                if tip.y > joint.y:
                    finger_folded += 1
            
            is_fist = finger_folded >= 3
            
            # Visual indicators
            if is_fist:
                cv2.putText(processed_frame, "✊ PAUSED", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                cv2.putText(processed_frame, "✋ DRAWING", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
            if finger_tip and not is_fist:
                cv2.circle(processed_frame, finger_tip, 10, (0, 255, 255), -1)
        
        return processed_frame, finger_tip, is_fist

    def release(self):
        self.hands.close()
