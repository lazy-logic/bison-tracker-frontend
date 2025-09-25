#!/usr/bin/env python3
"""
Test script to verify the enhanced dashboard components
"""

import os
import sys
import json
from datetime import datetime

def check_file_exists(filepath, description):
    """Check if a file exists and report status"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✓ {description}: {filepath} ({size} bytes)")
        return True
    else:
        print(f"✗ {description}: {filepath} NOT FOUND")
        return False

def check_imports():
    """Check if required Python packages are installed"""
    print("\n=== Checking Python Dependencies ===")
    
    packages = {
        'flask': 'Flask web framework',
        'flask_socketio': 'Flask-SocketIO for WebSocket',
        'flask_cors': 'Flask-CORS for cross-origin requests',
        'cv2': 'OpenCV for video processing',
        'numpy': 'NumPy for numerical operations',
        'ultralytics': 'YOLO implementation',
        'sqlite3': 'SQLite database (built-in)',
        'PIL': 'Pillow for image processing'
    }
    
    missing = []
    for package, description in packages.items():
        try:
            if package == 'cv2':
                import cv2
            elif package == 'flask':
                import flask
            elif package == 'flask_socketio':
                import flask_socketio
            elif package == 'flask_cors':
                import flask_cors
            elif package == 'numpy':
                import numpy
            elif package == 'ultralytics':
                import ultralytics
            elif package == 'sqlite3':
                import sqlite3
            elif package == 'PIL':
                from PIL import Image
            print(f"✓ {description}: {package}")
        except ImportError:
            print(f"✗ {description}: {package} NOT INSTALLED")
            missing.append(package)
    
    return missing

def check_project_structure():
    """Check if all required files and directories exist"""
    print("\n=== Checking Project Structure ===")
    
    files_to_check = [
        # Core files
        ('best.pt', 'YOLO model weights'),
        ('args.yaml', 'ByteTrack configuration'),
        ('requirements.txt', 'Python dependencies'),
        
        # Dashboard files
        ('flask_dashboard.py', 'Standard Flask dashboard'),
        ('enhanced_dashboard.py', 'Enhanced dashboard with analytics'),
        ('analytics_engine.py', 'Analytics processing engine'),
        
        # Templates
        ('templates/dashboard.html', 'Standard dashboard template'),
        ('templates/enhanced_dashboard.html', 'Enhanced dashboard template'),
        
        # Static files
        ('static/css/dashboard.css', 'Dashboard styles'),
        ('static/js/analytics.js', 'Analytics JavaScript'),
        ('static/js/charts.js', 'Chart management JavaScript'),
        
        # Batch scripts
        ('setup_env.bat', 'Virtual environment setup'),
        ('activate.bat', 'Virtual environment activation'),
        ('run_dashboard.bat', 'Dashboard launcher'),
        
        # Original files
        ('rtsp_bison_tracker_2.py', 'RTSP streaming server'),
        ('track.py', 'Video tracking script')
    ]
    
    all_exist = True
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    # Check directories
    print("\n=== Checking Directories ===")
    dirs_to_check = [
        'templates',
        'static',
        'static/css',
        'static/js'
    ]
    
    for dir_path in dirs_to_check:
        if os.path.isdir(dir_path):
            print(f"✓ Directory: {dir_path}")
        else:
            print(f"✗ Directory: {dir_path} NOT FOUND")
            all_exist = False
    
    return all_exist

def test_analytics_engine():
    """Test the analytics engine initialization"""
    print("\n=== Testing Analytics Engine ===")
    
    try:
        from analytics_engine import BisonAnalytics
        
        # Initialize analytics
        analytics = BisonAnalytics(db_path="test_analytics.db")
        print("✓ Analytics engine initialized")
        
        # Test processing
        test_detections = [
            {
                'track_id': 1,
                'confidence': 0.85,
                'bbox': [100, 100, 200, 200],
                'class': 0
            }
        ]
        
        result = analytics.process_frame_detections('test_camera', test_detections, 1)
        print(f"✓ Frame processing test passed: {result}")
        
        # Get statistics
        stats = analytics.get_statistics()
        print(f"✓ Statistics retrieval: {json.dumps(stats, indent=2)}")
        
        # Clean up test database
        if os.path.exists("test_analytics.db"):
            os.remove("test_analytics.db")
            
        return True
        
    except Exception as e:
        print(f"✗ Analytics engine test failed: {e}")
        return False

def test_flask_routes():
    """Test Flask application routes"""
    print("\n=== Testing Flask Routes ===")
    
    try:
        # Test standard dashboard
        if os.path.exists('flask_dashboard.py'):
            print("✓ Standard dashboard found")
            
        # Test enhanced dashboard
        if os.path.exists('enhanced_dashboard.py'):
            print("✓ Enhanced dashboard found")
            
            # Import and check routes
            from enhanced_dashboard import app
            
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append(str(rule))
            
            print(f"✓ Found {len(routes)} routes:")
            for route in sorted(routes)[:10]:  # Show first 10 routes
                print(f"  - {route}")
                
        return True
        
    except Exception as e:
        print(f"✗ Flask routes test failed: {e}")
        return False

def generate_test_report():
    """Generate a comprehensive test report"""
    print("\n" + "=" * 60)
    print("BISONGUARD ENHANCED DASHBOARD - TEST REPORT")
    print("=" * 60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check virtual environment
    print("\n=== Virtual Environment ===")
    if hasattr(sys, 'prefix') and 'venv' in sys.prefix:
        print("✓ Running in virtual environment")
    else:
        print("⚠ Not running in virtual environment")
        print("  Recommendation: Run 'activate.bat' first")
    
    # Run all checks
    missing_packages = check_imports()
    structure_ok = check_project_structure()
    analytics_ok = test_analytics_engine()
    routes_ok = test_flask_routes()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if missing_packages:
        print(f"⚠ Missing packages: {', '.join(missing_packages)}")
        print("  Run: pip install -r requirements.txt")
    else:
        print("✓ All Python dependencies installed")
    
    if structure_ok:
        print("✓ Project structure complete")
    else:
        print("⚠ Some files missing - check above for details")
    
    if analytics_ok:
        print("✓ Analytics engine functional")
    else:
        print("⚠ Analytics engine issues detected")
    
    if routes_ok:
        print("✓ Flask routes configured")
    else:
        print("⚠ Flask route issues detected")
    
    # Final recommendation
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    
    if missing_packages:
        print("1. Install missing packages:")
        print("   activate.bat")
        print("   pip install -r requirements.txt")
    
    if structure_ok and not missing_packages:
        print("✓ System ready! You can now run:")
        print("   run_dashboard.bat")
        print("\nOr manually:")
        print("   activate.bat")
        print("   python enhanced_dashboard.py")
        print("\nThen open: http://localhost:5000")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    generate_test_report()
