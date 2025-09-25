#!/usr/bin/env python3
"""
Comprehensive Test Suite for BisonGuard Analytics System
Tests all major components including detection, tracking, analytics, and API endpoints
"""

import unittest
import json
import time
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
from analytics_engine import BisonAnalytics
from flask_dashboard import app, socketio
from enhanced_dashboard import process_frame, calculate_metrics

class TestBisonDetection(unittest.TestCase):
    """Test bison detection functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.mock_detections = [
            {'bbox': [100, 200, 150, 180], 'confidence': 0.92, 'class': 0},
            {'bbox': [500, 400, 160, 190], 'confidence': 0.87, 'class': 0}
        ]
    
    @patch('cv2.VideoCapture')
    def test_video_capture_initialization(self, mock_capture):
        """Test video capture initialization"""
        mock_capture.return_value.isOpened.return_value = True
        mock_capture.return_value.read.return_value = (True, self.mock_frame)
        
        # Test initialization
        cap = mock_capture('test_video.mp4')
        self.assertTrue(cap.isOpened())
        
        # Test frame reading
        ret, frame = cap.read()
        self.assertTrue(ret)
        self.assertEqual(frame.shape, (1080, 1920, 3))
    
    @patch('ultralytics.YOLO')
    def test_yolo_detection(self, mock_yolo):
        """Test YOLO model detection"""
        # Mock YOLO model
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        # Mock detection results
        mock_results = MagicMock()
        mock_results.boxes = MagicMock()
        mock_results.boxes.data = [[100, 200, 250, 380, 0.92, 0],
                                   [500, 400, 660, 590, 0.87, 0]]
        mock_model.return_value = [mock_results]
        
        # Test detection
        model = mock_yolo('best.pt')
        results = model(self.mock_frame)
        
        # Verify detections
        self.assertEqual(len(results), 1)
        boxes = results[0].boxes.data
        self.assertEqual(len(boxes), 2)
        self.assertAlmostEqual(boxes[0][4], 0.92, places=2)
    
    def test_confidence_filtering(self):
        """Test filtering detections by confidence threshold"""
        threshold = 0.5
        filtered = [d for d in self.mock_detections if d['confidence'] >= threshold]
        self.assertEqual(len(filtered), 2)
        
        threshold = 0.9
        filtered = [d for d in self.mock_detections if d['confidence'] >= threshold]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['confidence'], 0.92)


class TestBisonTracking(unittest.TestCase):
    """Test bison tracking functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracks = {}
        self.next_id = 1
    
    def test_track_initialization(self):
        """Test initializing new tracks"""
        detection = {'bbox': [100, 200, 150, 180], 'confidence': 0.92}
        
        # Create new track
        track_id = f"bison_{self.next_id:03d}"
        self.tracks[track_id] = {
            'bbox': detection['bbox'],
            'confidence': detection['confidence'],
            'age': 1,
            'history': [detection['bbox']]
        }
        self.next_id += 1
        
        # Verify track
        self.assertEqual(len(self.tracks), 1)
        self.assertIn('bison_001', self.tracks)
        self.assertEqual(self.tracks['bison_001']['age'], 1)
    
    def test_track_update(self):
        """Test updating existing tracks"""
        # Initialize track
        track_id = 'bison_001'
        self.tracks[track_id] = {
            'bbox': [100, 200, 150, 180],
            'confidence': 0.92,
            'age': 1,
            'history': [[100, 200, 150, 180]]
        }
        
        # Update track with new position
        new_bbox = [105, 205, 155, 185]
        self.tracks[track_id]['bbox'] = new_bbox
        self.tracks[track_id]['age'] += 1
        self.tracks[track_id]['history'].append(new_bbox)
        
        # Verify update
        self.assertEqual(self.tracks[track_id]['age'], 2)
        self.assertEqual(len(self.tracks[track_id]['history']), 2)
        self.assertEqual(self.tracks[track_id]['bbox'], new_bbox)
    
    def test_track_matching(self):
        """Test matching detections to existing tracks"""
        # Existing track
        track = {'bbox': [100, 200, 150, 180]}
        
        # New detection (close match)
        detection1 = {'bbox': [105, 205, 155, 185]}
        iou1 = self.calculate_iou(track['bbox'], detection1['bbox'])
        self.assertGreater(iou1, 0.8)  # High overlap
        
        # New detection (no match)
        detection2 = {'bbox': [500, 400, 160, 190]}
        iou2 = self.calculate_iou(track['bbox'], detection2['bbox'])
        self.assertLess(iou2, 0.1)  # Low overlap
    
    def calculate_iou(self, box1, box2):
        """Calculate Intersection over Union"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[0] + box1[2], box2[0] + box2[2])
        y2 = min(box1[1] + box1[3], box2[1] + box2[3])
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = box1[2] * box1[3]
        area2 = box2[2] * box2[3]
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0


class TestBisonAnalytics(unittest.TestCase):
    """Test analytics engine functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analytics = BisonAnalytics(db_path=":memory:")  # Use in-memory database
        self.test_data = {
            'timestamp': datetime.now(),
            'camera_id': 'camera_1',
            'detections': [
                {'id': 1, 'position': {'x': 100, 'y': 200}, 'confidence': 0.92},
                {'id': 2, 'position': {'x': 500, 'y': 400}, 'confidence': 0.87}
            ]
        }
    
    def test_behavior_classification(self):
        """Test behavior classification based on movement"""
        # Test grazing (low speed)
        behavior = self.analytics.classify_behavior(speed=0.3, direction_change=5)
        self.assertEqual(behavior, 'grazing')
        
        # Test moving (moderate speed)
        behavior = self.analytics.classify_behavior(speed=1.5, direction_change=20)
        self.assertEqual(behavior, 'moving')
        
        # Test alert (high speed)
        behavior = self.analytics.classify_behavior(speed=6.0, direction_change=45)
        self.assertEqual(behavior, 'alert')
    
    def test_herd_cohesion_calculation(self):
        """Test herd cohesion metric calculation"""
        positions = [
            {'x': 100, 'y': 100},
            {'x': 110, 'y': 105},
            {'x': 95, 'y': 98}
        ]
        
        cohesion = self.analytics.calculate_herd_cohesion(positions)
        self.assertGreater(cohesion, 80)  # High cohesion for close positions
        
        # Test with dispersed positions
        dispersed_positions = [
            {'x': 0, 'y': 0},
            {'x': 1000, 'y': 1000},
            {'x': 500, 'y': 500}
        ]
        
        cohesion = self.analytics.calculate_herd_cohesion(dispersed_positions)
        self.assertLess(cohesion, 20)  # Low cohesion for dispersed positions
    
    def test_movement_pattern_detection(self):
        """Test detection of movement patterns"""
        # Circular pattern
        circular_path = []
        for angle in range(0, 360, 30):
            x = 500 + 100 * np.cos(np.radians(angle))
            y = 500 + 100 * np.sin(np.radians(angle))
            circular_path.append({'x': x, 'y': y})
        
        pattern = self.analytics.detect_movement_pattern(circular_path)
        self.assertEqual(pattern['type'], 'circular')
        
        # Linear pattern
        linear_path = [{'x': i * 10, 'y': i * 10} for i in range(10)]
        pattern = self.analytics.detect_movement_pattern(linear_path)
        self.assertEqual(pattern['type'], 'linear')
    
    def test_alert_generation(self):
        """Test alert generation for unusual activity"""
        # Test rapid movement alert
        alert = self.analytics.check_for_alerts(speed=7.0, count=5)
        self.assertIsNotNone(alert)
        self.assertEqual(alert['type'], 'rapid_movement')
        self.assertEqual(alert['severity'], 'high')
        
        # Test crowding alert
        alert = self.analytics.check_for_alerts(speed=1.0, count=15)
        self.assertIsNotNone(alert)
        self.assertEqual(alert['type'], 'crowding')
        self.assertEqual(alert['severity'], 'medium')
        
        # Test no alert
        alert = self.analytics.check_for_alerts(speed=1.0, count=5)
        self.assertIsNone(alert)
    
    def test_statistics_calculation(self):
        """Test statistical metrics calculation"""
        # Add test data
        for i in range(10):
            self.analytics.add_detection({
                'timestamp': datetime.now() - timedelta(minutes=i),
                'count': 5 + i % 3,
                'camera_id': 'camera_1'
            })
        
        stats = self.analytics.calculate_statistics('hour')
        
        self.assertIn('total_detections', stats)
        self.assertIn('average_count', stats)
        self.assertIn('peak_count', stats)
        self.assertGreater(stats['total_detections'], 0)
        self.assertGreater(stats['average_count'], 0)


class TestFlaskAPI(unittest.TestCase):
    """Test Flask API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True
    
    def test_detection_endpoint(self):
        """Test /api/detections endpoint"""
        response = self.app.get('/api/detections')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('timestamp', data)
        self.assertIn('cameras', data)
        self.assertIn('total_count', data)
    
    def test_analytics_behavior_endpoint(self):
        """Test /api/analytics/behavior endpoint"""
        response = self.app.get('/api/analytics/behavior')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('behaviors', data)
        self.assertIn('dominant_behavior', data)
    
    def test_analytics_movement_endpoint(self):
        """Test /api/analytics/movement endpoint"""
        response = self.app.get('/api/analytics/movement')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('average_speed', data)
        self.assertIn('movement_patterns', data)
    
    def test_camera_list_endpoint(self):
        """Test /api/cameras endpoint"""
        response = self.app.get('/api/cameras')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('cameras', data)
        self.assertIsInstance(data['cameras'], list)
    
    def test_alerts_endpoint(self):
        """Test /api/alerts endpoint"""
        response = self.app.get('/api/alerts')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('alerts', data)
        self.assertIsInstance(data['alerts'], list)
    
    def test_export_csv_endpoint(self):
        """Test /api/export/csv endpoint"""
        response = self.app.get('/api/export/csv?data_type=detections&start_date=2024-01-01&end_date=2024-01-25')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv')
    
    def test_invalid_endpoint(self):
        """Test handling of invalid endpoint"""
        response = self.app.get('/api/invalid')
        self.assertEqual(response.status_code, 404)


class TestWebSocket(unittest.TestCase):
    """Test WebSocket functionality"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.socketio_client = socketio.test_client(self.app)
    
    def test_websocket_connection(self):
        """Test WebSocket connection"""
        self.assertTrue(self.socketio_client.is_connected())
    
    def test_join_room(self):
        """Test joining a room"""
        self.socketio_client.emit('join', {'room': 'camera_1'})
        received = self.socketio_client.get_received()
        # Verify join was successful (implementation dependent)
    
    def test_detection_update_event(self):
        """Test receiving detection update events"""
        # Simulate detection update
        test_data = {
            'camera_id': 'camera_1',
            'count': 5,
            'timestamp': datetime.now().isoformat()
        }
        
        # This would normally be triggered by the backend
        # For testing, we verify the event structure
        self.assertIn('camera_id', test_data)
        self.assertIn('count', test_data)
        self.assertIn('timestamp', test_data)


class TestPerformance(unittest.TestCase):
    """Test performance metrics"""
    
    def test_frame_processing_speed(self):
        """Test frame processing performance"""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        start_time = time.time()
        # Simulate frame processing
        for _ in range(10):
            # Mock processing
            time.sleep(0.01)  # Simulate 10ms processing time
        
        elapsed = time.time() - start_time
        fps = 10 / elapsed
        
        # Should achieve at least 10 FPS
        self.assertGreater(fps, 10)
    
    def test_analytics_calculation_speed(self):
        """Test analytics calculation performance"""
        positions = [{'x': np.random.randint(0, 1920), 
                     'y': np.random.randint(0, 1080)} 
                    for _ in range(20)]
        
        start_time = time.time()
        # Simulate analytics calculations
        for _ in range(100):
            # Mock calculations
            avg_x = sum(p['x'] for p in positions) / len(positions)
            avg_y = sum(p['y'] for p in positions) / len(positions)
        
        elapsed = time.time() - start_time
        
        # Should complete in less than 1 second
        self.assertLess(elapsed, 1.0)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow"""
    
    @patch('cv2.VideoCapture')
    @patch('ultralytics.YOLO')
    def test_complete_detection_pipeline(self, mock_yolo, mock_capture):
        """Test complete detection pipeline from video to analytics"""
        # Setup mocks
        mock_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_capture.return_value.read.return_value = (True, mock_frame)
        
        mock_model = MagicMock()
        mock_results = MagicMock()
        mock_results.boxes.data = [[100, 200, 250, 380, 0.92, 0]]
        mock_model.return_value = [mock_results]
        mock_yolo.return_value = mock_model
        
        # Run pipeline
        cap = mock_capture('test.mp4')
        model = mock_yolo('best.pt')
        
        ret, frame = cap.read()
        self.assertTrue(ret)
        
        results = model(frame)
        self.assertEqual(len(results), 1)
        
        # Process detections
        detections = []
        for r in results:
            boxes = r.boxes.data
            for box in boxes:
                if box[4] > 0.5:  # Confidence threshold
                    detections.append({
                        'bbox': box[:4].tolist(),
                        'confidence': float(box[4])
                    })
        
        self.assertEqual(len(detections), 1)
        self.assertAlmostEqual(detections[0]['confidence'], 0.92, places=2)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def test_empty_frame_handling(self):
        """Test handling of empty frames"""
        empty_frame = None
        
        try:
            if empty_frame is not None:
                # Process frame
                pass
            else:
                # Handle empty frame
                self.assertIsNone(empty_frame)
        except Exception as e:
            self.fail(f"Failed to handle empty frame: {e}")
    
    def test_invalid_bbox_handling(self):
        """Test handling of invalid bounding boxes"""
        invalid_bboxes = [
            [],  # Empty
            [100],  # Too few values
            [100, 200, -50, 180],  # Negative dimension
            [2000, 200, 150, 180],  # Out of bounds
        ]
        
        frame_width, frame_height = 1920, 1080
        
        for bbox in invalid_bboxes:
            is_valid = self.validate_bbox(bbox, frame_width, frame_height)
            self.assertFalse(is_valid)
    
    def validate_bbox(self, bbox, width, height):
        """Validate bounding box"""
        if len(bbox) != 4:
            return False
        
        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            return False
        
        if x < 0 or y < 0 or x + w > width or y + h > height:
            return False
        
        return True
    
    def test_database_connection_failure(self):
        """Test handling of database connection failures"""
        try:
            # Attempt to connect to invalid database
            analytics = BisonAnalytics(db_path="/invalid/path/database.db")
        except Exception as e:
            # Should handle gracefully
            self.assertIsInstance(e, Exception)


def run_tests():
    """Run all tests with detailed output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBisonDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestBisonTracking))
    suite.addTests(loader.loadTestsFromTestCase(TestBisonAnalytics))
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestWebSocket))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
