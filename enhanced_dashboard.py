#!/usr/bin/env python3
"""
Enhanced Flask Dashboard for BisonGuard with Advanced Analytics
Real-time processing of live camera feeds with comprehensive analytics
"""

import os
import json
import time
import threading
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, request, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import io
import base64
from PIL import Image

# Import analytics engine and stream manager
from analytics_engine import BisonAnalytics
from rtsp_bison_tracker_2 import StreamManager

# Import YOLO for detection
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: YOLO not available. Running in demo mode.")

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bisonguard-secret-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize analytics engine
analytics = BisonAnalytics(db_path="bisonguard_analytics.db")

# Camera configuration
CAMERAS = {
    'camera_1': {
        'name': 'North Pasture',
        'url': 'rtsps://cr-14.hostedcloudvideo.com:443/publish-cr/_definst_/G0W2EP7IKAXYETM1ANDVQ6DBRXNXCN7VK3MM7SP9/6b55ae911a8dbd2bd7d3a75ae4547acc976d0b9e?action=PLAY',
        'enabled': True,
        'zone': 'north',
        'resolution': (1920, 1080)
    },
    'camera_2': {
        'name': 'South Pasture',
        'url': 'rtsps://cr-14.hostedcloudvideo.com:443/publish-cr/_definst_/XQYKDKIHA6RIQKST9PIKRE77D77547OU9D091HNA/6b55ae911a8dbd2bd7d3a75ae4547acc976d0b9e?action=PLAY',
        'enabled': True,
        'zone': 'south',
        'resolution': (1920, 1080)
    }
}

# Model configuration
MODEL_PATH = "best.pt"
TRACKER_CONFIG = "args.yaml"
MIN_CONFIDENCE = 0.3

# Global storage
stream_managers = {}
model = None
frame_processors = {}

# ─── FRAME PROCESSOR ───────────────────────────────────────────────────────────
class FrameProcessor:
    """Process frames with YOLO detection and tracking"""
    
    def __init__(self, camera_id: str, model_path: str, tracker_config: str):
        self.camera_id = camera_id
        self.model = None
        self.tracker_config = tracker_config
        self.frame_count = 0
        
        if YOLO_AVAILABLE and os.path.exists(model_path):
            try:
                self.model = YOLO(model_path)
                print(f"✓ Model loaded for {camera_id}")
            except Exception as e:
                print(f"✗ Failed to load model for {camera_id}: {e}")
                
    def process_frame(self, frame):
        """Process a single frame and return annotated frame + detections"""
        self.frame_count += 1
        detections = []
        
        if self.model:
            try:
                # Run YOLO detection and tracking
                results = self.model.track(
                    source=frame,
                    tracker=self.tracker_config if os.path.exists(self.tracker_config) else "bytetrack.yaml",
                    conf=MIN_CONFIDENCE,
                    persist=True,
                    verbose=False
                )[0]
                
                # Extract detections
                boxes = results.boxes
                if boxes is not None:
                    coords = boxes.xyxy.tolist()
                    cls_list = boxes.cls.tolist()
                    ids_tensor = boxes.id
                    id_list = ids_tensor.tolist() if ids_tensor is not None else [None]*len(cls_list)
                    conf_list = boxes.conf.tolist()
                    
                    # Process each detection
                    for (x1, y1, x2, y2), tid, cls, conf in zip(coords, id_list, cls_list, conf_list):
                        detection = {
                            'track_id': int(tid) if tid else None,
                            'confidence': float(conf),
                            'bbox': [float(x1), float(y1), float(x2), float(y2)],
                            'class': int(cls)
                        }
                        detections.append(detection)
                        
                        # Draw on frame
                        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
                        
                        # Color based on confidence
                        color_intensity = int(255 * conf)
                        color = (0, color_intensity, 255 - color_intensity)
                        
                        # Draw bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        
                        # Draw label with background
                        label = f"Bison #{tid} ({conf:.2f})" if tid else f"Bison ({conf:.2f})"
                        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                        cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                                    (x1 + label_size[0], y1), color, -1)
                        cv2.putText(frame, label, (x1, y1 - 5),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
            except Exception as e:
                print(f"Detection error on {self.camera_id}: {e}")
                
        # Send detections to analytics engine
        analytics_result = analytics.process_frame_detections(
            self.camera_id, detections, self.frame_count
        )
        
        # Add overlay information
        self._add_overlay(frame, len(detections), analytics_result)
        
        return frame, detections, analytics_result
        
    def _add_overlay(self, frame, count, analytics_result):
        """Add information overlay to frame"""
        h, w = frame.shape[:2]
        
        # Semi-transparent background for text
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (350, 120), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        # Add text
        cv2.putText(frame, f"Bison Count: {count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, f"Camera: {CAMERAS[self.camera_id]['name']}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Frame: {self.frame_count}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (w - 250, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add alerts if any
        if analytics_result.get('alerts'):
            alert_text = f"ALERT: {analytics_result['alerts'][0]['message']}"
            cv2.putText(frame, alert_text, (10, h - 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

# ─── ENHANCED STREAM MANAGER ──────────────────────────────────────────────────
class EnhancedStreamManager:
    """Enhanced stream manager with frame processing"""
    
    def __init__(self, camera_id: str, camera_config: dict):
        self.camera_id = camera_id
        self.config = camera_config
        self.cap = None
        self.running = False
        self.current_frame = None
        self.processed_frame = None
        self.frame_lock = threading.Lock()
        self.processor = FrameProcessor(camera_id, MODEL_PATH, TRACKER_CONFIG)
        self.thread = None
        self.fps = 0
        self.last_fps_time = time.time()
        self.fps_counter = 0
        
    def start(self):
        """Start streaming and processing"""
        print(f"Starting stream for {self.camera_id}: {self.config['name']}")
        self.cap = cv2.VideoCapture(self.config['url'])
        
        if not self.cap.isOpened():
            print(f"Failed to open stream for {self.camera_id}")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()
        return True
        
    def _stream_loop(self):
        """Main streaming and processing loop"""
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print(f"Failed to read frame from {self.camera_id}, reconnecting...")
                self.cap.release()
                time.sleep(2)
                self.cap = cv2.VideoCapture(self.config['url'])
                continue
                
            # Update FPS
            self.fps_counter += 1
            now = time.time()
            if now - self.last_fps_time >= 1.0:
                self.fps = self.fps_counter / (now - self.last_fps_time)
                self.fps_counter = 0
                self.last_fps_time = now
                
            # Process frame
            processed_frame, detections, analytics_result = self.processor.process_frame(frame.copy())
            
            # Store frames
            with self.frame_lock:
                self.current_frame = frame
                self.processed_frame = processed_frame
                
            # Emit real-time updates via WebSocket
            socketio.emit('frame_processed', {
                'camera_id': self.camera_id,
                'detections': len(detections),
                'fps': self.fps,
                'timestamp': datetime.now().isoformat()
            })
            
            # Small delay to control processing rate
            time.sleep(0.03)  # ~30 FPS max
            
    def get_frame(self, processed=True):
        """Get current frame"""
        with self.frame_lock:
            if processed and self.processed_frame is not None:
                return self.processed_frame.copy()
            elif self.current_frame is not None:
                return self.current_frame.copy()
        return None
        
    def stop(self):
        """Stop streaming"""
        self.running = False
        if self.cap:
            self.cap.release()

# ─── VIDEO STREAMING ───────────────────────────────────────────────────────────
def generate_frames(camera_id, processed=True):
    """Generate frames for video streaming"""
    manager = stream_managers.get(camera_id)
    if not manager:
        return
        
    while True:
        frame = manager.get_frame(processed=processed)
        if frame is not None:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            time.sleep(0.1)

# ─── FLASK ROUTES ──────────────────────────────────────────────────────────────
@app.route('/')
def index():
    """Enhanced dashboard with analytics"""
    return render_template('enhanced_dashboard.html', cameras=CAMERAS)

@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    """Processed video stream"""
    if camera_id in stream_managers:
        return Response(generate_frames(camera_id, processed=True),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Camera not found", 404

@app.route('/raw_feed/<camera_id>')
def raw_feed(camera_id):
    """Raw video stream without processing"""
    if camera_id in stream_managers:
        return Response(generate_frames(camera_id, processed=False),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Camera not found", 404

@app.route('/api/analytics/stats')
def get_analytics_stats():
    """Get comprehensive analytics statistics"""
    return jsonify(analytics.get_statistics())

@app.route('/api/analytics/historical')
def get_historical_data():
    """Get historical analytics data"""
    hours = request.args.get('hours', 24, type=int)
    return jsonify(analytics.get_historical_data(hours))

@app.route('/api/analytics/heatmap/<camera_id>')
def get_heatmap(camera_id):
    """Get heatmap data for a camera"""
    heatmap_data = analytics.get_heatmap_data(camera_id)
    return jsonify({'camera_id': camera_id, 'heatmap': heatmap_data})

@app.route('/api/analytics/tracking_paths')
def get_tracking_paths():
    """Get recent tracking paths"""
    limit = request.args.get('limit', 10, type=int)
    return jsonify(analytics.get_tracking_paths(limit))

@app.route('/api/analytics/report')
def generate_report():
    """Generate comprehensive analytics report"""
    return jsonify(analytics.generate_report())

@app.route('/api/camera/<camera_id>/snapshot')
def get_snapshot(camera_id):
    """Get current snapshot from camera"""
    manager = stream_managers.get(camera_id)
    if manager:
        frame = manager.get_frame(processed=True)
        if frame is not None:
            # Convert to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                io_buf = io.BytesIO(buffer)
                return send_file(io_buf, mimetype='image/jpeg')
    return "Camera not found", 404

@app.route('/api/cameras/status')
def get_cameras_status():
    """Get status of all cameras"""
    status = {}
    for camera_id, manager in stream_managers.items():
        status[camera_id] = {
            'name': CAMERAS[camera_id]['name'],
            'online': manager.running,
            'fps': manager.fps,
            'frames_processed': manager.processor.frame_count
        }
    return jsonify(status)

# ─── WEBSOCKET EVENTS ──────────────────────────────────────────────────────────
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to BisonGuard Analytics'})
    
    # Send initial data
    emit('initial_data', {
        'cameras': list(CAMERAS.keys()),
        'stats': analytics.get_statistics()
    })

@socketio.on('request_analytics')
def handle_analytics_request():
    """Handle request for current analytics"""
    emit('analytics_update', analytics.get_statistics())

@socketio.on('set_alert_threshold')
def handle_set_threshold(data):
    """Update alert thresholds"""
    alert_type = data.get('type')
    value = data.get('value')
    if alert_type in analytics.alert_thresholds:
        analytics.alert_thresholds[alert_type] = value
        emit('threshold_updated', {'type': alert_type, 'value': value})

# ─── BACKGROUND TASKS ──────────────────────────────────────────────────────────
def analytics_broadcaster():
    """Broadcast analytics updates to all clients"""
    while True:
        time.sleep(2)
        stats = analytics.get_statistics()
        socketio.emit('analytics_update', stats)
        
        # Check for alerts
        for camera_id in CAMERAS.keys():
            detections = analytics.current_detections.get(camera_id, [])
            if detections:
                socketio.emit('detection_event', {
                    'camera_id': camera_id,
                    'count': len(detections),
                    'timestamp': datetime.now().isoformat()
                })

def hourly_aggregator():
    """Aggregate hourly statistics"""
    while True:
        time.sleep(3600)  # Run every hour
        # This would aggregate and store hourly stats
        print("Running hourly aggregation...")

# ─── INITIALIZATION ────────────────────────────────────────────────────────────
def initialize_system():
    """Initialize all system components"""
    print("Initializing BisonGuard Enhanced Dashboard...")
    
    # Start camera streams
    for camera_id, config in CAMERAS.items():
        if config['enabled']:
            manager = EnhancedStreamManager(camera_id, config)
            if manager.start():
                stream_managers[camera_id] = manager
                print(f"✓ Camera {camera_id} initialized")
            else:
                print(f"✗ Failed to initialize {camera_id}")
                
    # Start background tasks
    threading.Thread(target=analytics_broadcaster, daemon=True).start()
    threading.Thread(target=hourly_aggregator, daemon=True).start()
    
    print("System initialization complete!")

# ─── MAIN EXECUTION ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("BisonGuard Enhanced Analytics Dashboard")
    print("=" * 60)
    
    # Initialize system
    initialize_system()
    
    # Start Flask app
    print(f"\nStarting dashboard on http://localhost:5000")
    print("=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
