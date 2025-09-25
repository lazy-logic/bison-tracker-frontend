#!/usr/bin/env python3
"""
Advanced Analytics Engine for BisonGuard
Processes real-time detection data and generates insights
"""

import json
import time
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional
import threading
import sqlite3
import os

class BisonAnalytics:
    """
    Comprehensive analytics engine for bison detection and tracking
    """
    
    def __init__(self, db_path: str = "bisonguard_analytics.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.heatmap_resolution = (100, 100) # Higher internal resolution
        
        # Real-time data structures
        self.current_detections = defaultdict(list)  # camera_id -> list of current detections
        self.tracking_history = defaultdict(lambda: deque(maxlen=1000))  # track_id -> position history
        self.movement_patterns = defaultdict(dict)  # track_id -> movement data
        self.zone_heatmap = defaultdict(lambda: np.zeros(self.heatmap_resolution))
        
        # Time-series data
        self.hourly_counts = deque(maxlen=24)  # Last 24 hours
        self.daily_counts = deque(maxlen=30)   # Last 30 days
        self.detection_confidence = deque(maxlen=1000)
        
        # Statistics
        self.stats = {
            'total_detections': 0,
            'unique_tracks': set(),
            'peak_count': 0,
            'peak_time': None,
            'avg_confidence': 0.0,
            'avg_dwell_time': 0.0,
            'total_alerts': 0,
            'cameras_active': 0
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            'high_activity': 10,      # More than 10 bison
            'low_confidence': 0.3,    # Below 30% confidence
            'rapid_movement': 50,     # Pixels per frame
            'crowd_detection': 15,    # Group threshold
            'zone_intrusion': None    # Special zones (can be configured)
        }
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for historical data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Detections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                camera_id TEXT,
                track_id INTEGER,
                confidence REAL,
                bbox_x1 REAL,
                bbox_y1 REAL,
                bbox_x2 REAL,
                bbox_y2 REAL,
                frame_number INTEGER
            )
        ''')
        
        # Tracking sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracking_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER UNIQUE,
                first_seen DATETIME,
                last_seen DATETIME,
                total_frames INTEGER,
                avg_confidence REAL,
                distance_traveled REAL,
                camera_id TEXT
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT,
                severity TEXT,
                camera_id TEXT,
                message TEXT,
                data JSON
            )
        ''')
        
        # Hourly aggregates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hourly_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour_timestamp DATETIME,
                camera_id TEXT,
                total_detections INTEGER,
                unique_tracks INTEGER,
                avg_confidence REAL,
                max_simultaneous INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Rebuild heatmap from historical data
        self._rebuild_heatmap_from_db()
        
    def _rebuild_heatmap_from_db(self):
        """Rebuild heatmap from historical detection data"""
        print("Rebuilding heatmap from historical data...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get recent detections (last 24 hours) to rebuild heatmap
            cursor.execute('''
                SELECT camera_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2
                FROM detections 
                WHERE timestamp > datetime('now', '-24 hours')
                AND bbox_x1 IS NOT NULL AND bbox_y1 IS NOT NULL
                AND bbox_x2 IS NOT NULL AND bbox_y2 IS NOT NULL
            ''')
            
            detections = cursor.fetchall()
            heatmap_counts = defaultdict(int)
            
            for camera_id, x1, y1, x2, y2 in detections:
                # Use the center of the bounding box for the heatmap
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                # Normalize coordinates to a higher resolution grid (e.g., 100x100)
                # and then aggregate to the visualization grid size in get_heatmap_data
                grid_x = int(center_x * (self.heatmap_resolution[0] / 1920))
                grid_y = int(center_y * (self.heatmap_resolution[1] / 1080))
                
                grid_x = min(grid_x, self.heatmap_resolution[0] - 1)
                grid_y = min(grid_y, self.heatmap_resolution[1] - 1)

                self.zone_heatmap[camera_id][grid_y, grid_x] += 1
                heatmap_counts[camera_id] += 1
            
            print(f"✓ Rebuilt heatmap with {len(detections)} detections")
            for camera_id, count in heatmap_counts.items():
                print(f"  - {camera_id}: {count} points")
                
        except Exception as e:
            print(f"Error rebuilding heatmap: {e}")
        finally:
            conn.close()
        
    def process_frame_detections(self, camera_id: str, detections: List[Dict], frame_number: int):
        """
        Process detections from a single frame
        
        Args:
            camera_id: Camera identifier
            detections: List of detection dictionaries with bbox, confidence, track_id
            frame_number: Current frame number
        """
        with self.lock:
            timestamp = datetime.now()
            
            # Store current detections
            self.current_detections[camera_id] = detections
            
            # Update statistics
            self.stats['total_detections'] += len(detections)
            self.stats['cameras_active'] = len([d for d in self.current_detections.values() if d])
            
            # Process each detection
            for detection in detections:
                track_id = detection.get('track_id')
                confidence = detection.get('confidence', 0)
                bbox = detection.get('bbox', [0, 0, 0, 0])  # [x1, y1, x2, y2]
                
                # Update confidence tracking
                self.detection_confidence.append(confidence)
                
                # Update unique tracks
                if track_id:
                    self.stats['unique_tracks'].add(track_id)
                    
                    # Track movement
                    self._track_movement(track_id, bbox, timestamp)
                    
                    # Update zone heatmap
                    self._update_heatmap(camera_id, bbox)
                
                # Store in database
                self._store_detection(camera_id, detection, frame_number)
                
            # Check for alerts
            alerts = self._check_alerts(camera_id, detections)
            
            # Update peak count
            current_count = len(detections)
            if current_count > self.stats['peak_count']:
                self.stats['peak_count'] = current_count
                self.stats['peak_time'] = timestamp
                
            # Update average confidence
            if self.detection_confidence:
                self.stats['avg_confidence'] = np.mean(list(self.detection_confidence))
                
        return {
            'count': len(detections),
            'alerts': alerts,
            'timestamp': timestamp.isoformat()
        }
        
    def _track_movement(self, track_id: int, bbox: List[float], timestamp: datetime):
        """Track movement patterns for individual bison"""
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        position = (center_x, center_y, timestamp)
        
        self.tracking_history[track_id].append(position)
        
        # Calculate movement metrics
        if len(self.tracking_history[track_id]) > 1:
            prev_pos = self.tracking_history[track_id][-2]
            
            # Calculate speed (pixels per second)
            time_diff = (timestamp - prev_pos[2]).total_seconds()
            if time_diff > 0:
                distance = np.sqrt((center_x - prev_pos[0])**2 + (center_y - prev_pos[1])**2)
                speed = distance / time_diff
                
                self.movement_patterns[track_id] = {
                    'current_speed': speed,
                    'avg_speed': np.mean([p.get('current_speed', 0) 
                                         for p in [self.movement_patterns.get(track_id, {})]]),
                    'total_distance': self.movement_patterns.get(track_id, {}).get('total_distance', 0) + distance,
                    'direction': np.arctan2(center_y - prev_pos[1], center_x - prev_pos[0])
                }
                
    def _update_heatmap(self, camera_id: str, bbox: List[float]):
        """Update zone heatmap for activity visualization"""
        # Normalize bbox coordinates to 10x10 grid
        grid_x = min(int(bbox[0] / 192), 9)  # Assuming 1920px width
        grid_y = min(int(bbox[1] / 108), 9)  # Assuming 1080px height
        
        self.zone_heatmap[camera_id][grid_y, grid_x] += 1
        
    def _check_alerts(self, camera_id: str, detections: List[Dict]) -> List[Dict]:
        """Check for alert conditions"""
        alerts = []
        
        # High activity alert
        if len(detections) > self.alert_thresholds['high_activity']:
            alert = {
                'type': 'high_activity',
                'severity': 'warning',
                'camera_id': camera_id,
                'message': f'High bison activity: {len(detections)} detected',
                'count': len(detections)
            }
            alerts.append(alert)
            self._store_alert(alert)
            
        # Low confidence alert
        if detections:
            avg_conf = np.mean([d.get('confidence', 0) for d in detections])
            if avg_conf < self.alert_thresholds['low_confidence']:
                alert = {
                    'type': 'low_confidence',
                    'severity': 'info',
                    'camera_id': camera_id,
                    'message': f'Low detection confidence: {avg_conf:.2f}',
                    'confidence': avg_conf
                }
                alerts.append(alert)
                
        # Rapid movement detection
        for track_id, movement in self.movement_patterns.items():
            if movement.get('current_speed', 0) > self.alert_thresholds['rapid_movement']:
                alert = {
                    'type': 'rapid_movement',
                    'severity': 'warning',
                    'camera_id': camera_id,
                    'message': f'Rapid movement detected for track {track_id}',
                    'track_id': track_id,
                    'speed': movement['current_speed']
                }
                alerts.append(alert)
                
        self.stats['total_alerts'] += len(alerts)
        return alerts
        
    def _store_detection(self, camera_id: str, detection: Dict, frame_number: int):
        """Store detection in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO detections (camera_id, track_id, confidence, 
                                  bbox_x1, bbox_y1, bbox_x2, bbox_y2, frame_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            camera_id,
            detection.get('track_id'),
            detection.get('confidence'),
            detection.get('bbox', [0,0,0,0])[0],
            detection.get('bbox', [0,0,0,0])[1],
            detection.get('bbox', [0,0,0,0])[2],
            detection.get('bbox', [0,0,0,0])[3],
            frame_number
        ))
        
        conn.commit()
        conn.close()
        
    def _store_alert(self, alert: Dict):
        """Store alert in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (alert_type, severity, camera_id, message, data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            alert['type'],
            alert['severity'],
            alert['camera_id'],
            alert['message'],
            json.dumps(alert)
        ))
        
        conn.commit()
        conn.close()
        
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        with self.lock:
            # Calculate additional metrics
            total_current = sum(len(d) for d in self.current_detections.values())
            
            # Movement statistics
            movement_stats = {}
            if self.movement_patterns:
                speeds = [m.get('current_speed', 0) for m in self.movement_patterns.values()]
                movement_stats = {
                    'avg_speed': np.mean(speeds) if speeds else 0,
                    'max_speed': max(speeds) if speeds else 0,
                    'moving_tracks': len([s for s in speeds if s > 5])  # Threshold for "moving"
                }
                
            return {
                'total_detections': self.stats['total_detections'],
                'current_count': total_current,
                'unique_tracks': len(self.stats['unique_tracks']),
                'peak_count': self.stats['peak_count'],
                'peak_time': self.stats['peak_time'].isoformat() if self.stats['peak_time'] else None,
                'avg_confidence': self.stats['avg_confidence'],
                'cameras_active': self.stats['cameras_active'],
                'total_alerts': self.stats['total_alerts'],
                'movement': movement_stats,
                'timestamp': datetime.now().isoformat()
            }
            
    def get_historical_data(self, hours: int = 24) -> Dict:
        """Get historical data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        
        # Get hourly counts
        cursor.execute('''
            SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                   COUNT(*) as count,
                   COUNT(DISTINCT track_id) as unique_tracks,
                   AVG(confidence) as avg_confidence
            FROM detections
            WHERE timestamp > ?
            GROUP BY hour
            ORDER BY hour
        ''', (since,))
        
        hourly_data = cursor.fetchall()
        
        # Get recent alerts
        cursor.execute('''
            SELECT * FROM alerts
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (since,))
        
        alerts = cursor.fetchall()
        
        conn.close()
        
        return {
            'hourly': [{'hour': h[0], 'count': h[1], 'unique': h[2], 'confidence': h[3]} 
                      for h in hourly_data],
            'alerts': [{'type': a[2], 'severity': a[3], 'message': a[5], 'timestamp': a[1]} 
                      for a in alerts]
        }
        
    def get_heatmap_data(self, camera_id: str) -> Dict:
        """Get heatmap data for visualization, aggregated for display."""
        with self.lock:
            if camera_id not in self.zone_heatmap:
                return {'max': 0, 'data': []}

            high_res_heatmap = self.zone_heatmap[camera_id]
            
            # Aggregate the high-resolution heatmap to a smaller size for visualization
            vis_grid_size = 20 
            aggregated_heatmap = np.zeros((vis_grid_size, vis_grid_size))
            
            scale_y = self.heatmap_resolution[0] / vis_grid_size
            scale_x = self.heatmap_resolution[1] / vis_grid_size

            for y in range(self.heatmap_resolution[0]):
                for x in range(self.heatmap_resolution[1]):
                    if high_res_heatmap[y, x] > 0:
                        agg_y = int(y / scale_y)
                        agg_x = int(x / scale_x)
                        aggregated_heatmap[agg_y, agg_x] += high_res_heatmap[y, x]

            if aggregated_heatmap.max() == 0:
                return {'max': 0, 'data': []}

            # Create data points for heatmap.js
            points = []
            for y in range(vis_grid_size):
                for x in range(vis_grid_size):
                    if aggregated_heatmap[y, x] > 0:
                        points.append({
                            'x': int(x * (800 / vis_grid_size)), # Scale to canvas size
                            'y': int(y * (450 / vis_grid_size)), # Scale to canvas size
                            'value': int(aggregated_heatmap[y, x])
                        })
            
            return {
                'max': int(np.max(aggregated_heatmap)),
                'data': points
            }
            
    def get_tracking_paths(self, limit: int = 10) -> Dict:
        """Get recent tracking paths for visualization"""
        with self.lock:
            paths = {}
            for track_id in list(self.tracking_history.keys())[-limit:]:
                positions = self.tracking_history[track_id]
                if positions:
                    paths[track_id] = [
                        {'x': p[0], 'y': p[1], 'time': p[2].isoformat()}
                        for p in positions
                    ]
            return paths
            
    def generate_report(self) -> Dict:
        """Generate comprehensive analytics report"""
        stats = self.get_statistics()
        historical = self.get_historical_data()
        
        # Calculate trends
        if historical['hourly']:
            counts = [h['count'] for h in historical['hourly']]
            trend = 'increasing' if len(counts) > 1 and counts[-1] > counts[0] else 'stable'
        else:
            trend = 'no data'
            
        return {
            'summary': stats,
            'historical': historical,
            'trend': trend,
            'generated_at': datetime.now().isoformat()
        }
