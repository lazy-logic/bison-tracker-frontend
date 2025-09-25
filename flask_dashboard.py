#!/usr/bin/env python3
"""
Flask Dashboard for BisonGuard - Real-time Bison Monitoring System
Integrates with existing YOLO model and RTSP streams for comprehensive analytics
"""

import os
import json
import time
import threading
import queue
from datetime import datetime, timedelta
from collections import deque
import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from ultralytics import YOLO

# Import your existing modules
from rtsp_bison_tracker_2 import StreamManager, HLSManager

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bisonguard-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Camera configuration - can be expanded for multiple cameras
CAMERAS = {
    'camera_1': {
        'name': 'North Field',
        'url': 'rtsps://cr-14.hostedcloudvideo.com:443/publish-cr/_definst_/G0W2EP7IKAXYETM1ANDVQ6DBRXNXCN7VK3MM7SP9/6b55ae911a8dbd2bd7d3a75ae4547acc976d0b9e?action=PLAY',
        'enabled': True
    },
    'camera_2': {
        'name': 'South Field', 
        'url': 'rtsps://cr-14.hostedcloudvideo.com:443/publish-cr/_definst_/XQYKDKIHA6RIQKST9PIKRE77D77547OU9D091HNA/6b55ae911a8dbd2bd7d3a75ae4547acc976d0b9e?action=PLAY',
        'enabled': True
    }
}

# Global storage for stream managers and analytics
stream_managers = {}
analytics_data = {
    'total_detections': 0,
    'active_tracks': {},
    'historical_counts': deque(maxlen=1000),  # Keep last 1000 data points
    'alerts': deque(maxlen=50),
    'camera_status': {},
    'peak_count': 0,
    'peak_time': None
}

# ─── ANALYTICS ENGINE ──────────────────────────────────────────────────────────
class AnalyticsEngine:
    """Processes detection data and generates insights"""
    
    def __init__(self):
        self.movement_patterns = {}
        self.confidence_history = deque(maxlen=100)
        self.detection_zones = {}  # For heatmap generation
        
    def process_detection(self, camera_id, detections):
        """Process new detections and update analytics"""
        timestamp = datetime.now()
        
        # Update detection count
        count = len(detections) if detections else 0
        analytics_data['historical_counts'].append({
            'timestamp': timestamp.isoformat(),
            'camera_id': camera_id,
            'count': count
        })
        
        # Check for peak count
        if count > analytics_data['peak_count']:
            analytics_data['peak_count'] = count
            analytics_data['peak_time'] = timestamp.isoformat()
            
        # Generate alert if unusual activity
        if count > 10:  # Threshold for alert
            alert = {
                'type': 'high_activity',
                'camera_id': camera_id,
                'message': f'High bison activity detected: {count} bison',
                'timestamp': timestamp.isoformat(),
                'severity': 'warning'
            }
            analytics_data['alerts'].append(alert)
            socketio.emit('alert', alert)
            
        # Update active tracks
        if detections:
            for detection in detections:
                track_id = detection.get('track_id')
                if track_id:
                    analytics_data['active_tracks'][track_id] = {
                        'camera_id': camera_id,
                        'last_seen': timestamp.isoformat(),
                        'confidence': detection.get('confidence', 0)
                    }
                    
        # Emit real-time update
        socketio.emit('detection_update', {
            'camera_id': camera_id,
            'count': count,
            'timestamp': timestamp.isoformat()
        })
        
    def get_statistics(self):
        """Generate comprehensive statistics"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Calculate hourly statistics
        recent_counts = [
            d['count'] for d in analytics_data['historical_counts']
            if datetime.fromisoformat(d['timestamp']) > hour_ago
        ]
        
        stats = {
            'total_detections': analytics_data['total_detections'],
            'current_active_tracks': len(analytics_data['active_tracks']),
            'peak_count_today': analytics_data['peak_count'],
            'peak_time': analytics_data['peak_time'],
            'hourly_average': np.mean(recent_counts) if recent_counts else 0,
            'hourly_max': max(recent_counts) if recent_counts else 0,
            'cameras_online': sum(1 for s in analytics_data['camera_status'].values() if s == 'online'),
            'total_cameras': len(CAMERAS),
            'recent_alerts': list(analytics_data['alerts'])[-5:]  # Last 5 alerts
        }
        
        return stats

analytics_engine = AnalyticsEngine()

# ─── STREAM PROCESSING ─────────────────────────────────────────────────────────
def initialize_streams():
    """Initialize all camera streams"""
    for camera_id, config in CAMERAS.items():
        if config['enabled']:
            try:
                manager = StreamManager(config['url'], apply_model=True)
                manager.start_stream()
                stream_managers[camera_id] = manager
                analytics_data['camera_status'][camera_id] = 'online'
                print(f"✓ Camera {camera_id} ({config['name']}) initialized")
            except Exception as e:
                print(f"✗ Failed to initialize {camera_id}: {e}")
                analytics_data['camera_status'][camera_id] = 'offline'

def generate_frames(camera_id):
    """Generate frames for video streaming"""
    manager = stream_managers.get(camera_id)
    if not manager:
        return
        
    while True:
        frame = manager.get_current_frame()
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
    """Main dashboard page"""
    return render_template('dashboard.html', cameras=CAMERAS)

@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    """Video streaming route for specific camera"""
    if camera_id in stream_managers:
        return Response(generate_frames(camera_id),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Camera not found", 404

@app.route('/api/stats')
def get_stats():
    """Get current statistics"""
    return jsonify(analytics_engine.get_statistics())

@app.route('/api/camera/<camera_id>/stats')
def get_camera_stats(camera_id):
    """Get statistics for specific camera"""
    manager = stream_managers.get(camera_id)
    if manager:
        return jsonify(manager.stats)
    return jsonify({'error': 'Camera not found'}), 404

@app.route('/api/historical')
def get_historical_data():
    """Get historical detection data"""
    limit = request.args.get('limit', 100, type=int)
    data = list(analytics_data['historical_counts'])[-limit:]
    return jsonify(data)

@app.route('/api/alerts')
def get_alerts():
    """Get recent alerts"""
    return jsonify(list(analytics_data['alerts']))

@app.route('/api/cameras')
def get_cameras():
    """Get camera configuration and status"""
    camera_info = []
    for camera_id, config in CAMERAS.items():
        info = config.copy()
        info['id'] = camera_id
        info['status'] = analytics_data['camera_status'].get(camera_id, 'unknown')
        if camera_id in stream_managers:
            info['stats'] = stream_managers[camera_id].stats
        camera_info.append(info)
    return jsonify(camera_info)

# ─── WEBSOCKET EVENTS ──────────────────────────────────────────────────────────
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to BisonGuard Dashboard'})
    emit('initial_stats', analytics_engine.get_statistics())

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('request_stats')
def handle_stats_request():
    """Handle request for current stats"""
    emit('stats_update', analytics_engine.get_statistics())

# ─── BACKGROUND TASKS ──────────────────────────────────────────────────────────
def stats_broadcaster():
    """Broadcast statistics to all connected clients periodically"""
    while True:
        time.sleep(2)  # Update every 2 seconds
        stats = analytics_engine.get_statistics()
        socketio.emit('stats_update', stats)

def detection_processor():
    """Process detections from all cameras"""
    while True:
        for camera_id, manager in stream_managers.items():
            if manager and manager.stats:
                # Simulate detection processing (integrate with your actual detection data)
                detections = []  # This would come from your YOLO processing
                analytics_engine.process_detection(camera_id, detections)
        time.sleep(1)

# ─── MAIN EXECUTION ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("BisonGuard Flask Dashboard")
    print("=" * 60)
    
    # Initialize camera streams
    print("\nInitializing camera streams...")
    initialize_streams()
    
    # Start background tasks
    print("\nStarting background tasks...")
    threading.Thread(target=stats_broadcaster, daemon=True).start()
    threading.Thread(target=detection_processor, daemon=True).start()
    
    # Start Flask app with SocketIO
    print(f"\nStarting dashboard server on http://localhost:5000")
    print("=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
