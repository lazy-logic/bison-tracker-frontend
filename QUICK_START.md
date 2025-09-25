# BisonGuard Enhanced Dashboard - Quick Start Guide

## Prerequisites Check
Run this first to verify your setup:
```bash
python test_dashboard.py
```

## One-Click Launch (Recommended)
Simply double-click or run:
```bash
run_dashboard.bat
```
This will:
- Set up virtual environment (if needed)
- Install all dependencies
- Launch the enhanced dashboard
- Open at http://localhost:5000

## Manual Setup (Step-by-Step)

### 1. First Time Setup
```bash
# Create and activate virtual environment
setup_env.bat
```

### 2. Daily Use
```bash
# Activate virtual environment
activate.bat

# Run the enhanced dashboard
python enhanced_dashboard.py
```

### 3. Access the Dashboard
Open your browser to: **http://localhost:5000**

## Dashboard Features

### Live View Tab
- **Real-time video feeds** from multiple cameras
- **Bison detection overlays** with bounding boxes
- **Track IDs** for individual animals
- **FPS and detection count** per camera
- **Snapshot capability** for each feed

### Analytics Tab
- **24-hour timeline chart** of detections
- **Detection distribution** across cameras
- **Confidence score histogram**
- **Movement pattern analysis**

### Activity Heatmap Tab
- **Visual heatmap** showing bison activity zones
- **Per-camera heatmaps** for detailed analysis
- **Intensity indicators** for high-traffic areas

### Tracking Paths Tab
- **Movement trajectories** of tracked bison
- **Path visualization** over time
- **Speed and direction analysis**
 
### Settings Tab
- **Alert threshold configuration**
- **High activity alerts** (customizable)
- **Low confidence warnings**
- **Rapid movement detection**

## Real-Time Analytics

The dashboard provides:
- **Current bison count** across all cameras
- **Unique tracks** being monitored
- **Peak count** for the day
- **Average confidence** scores
- **Movement speed** analysis
- **Alert notifications** in real-time

## Troubleshooting

### Dashboard won't start?
```bash
# Check dependencies
python test_dashboard.py

# Reinstall if needed
activate.bat
pip install -r requirements.txt
```

### Camera feeds not showing?
1. Verify RTSP URLs in `enhanced_dashboard.py`
2. Check network connectivity
3. Ensure cameras are online

### No detections appearing?
1. Verify `best.pt` model file exists
2. Check `args.yaml` configuration
3. Ensure MIN_CONFIDENCE is not too high (default: 0.3)

### Port 5000 already in use?
Edit `enhanced_dashboard.py` and change:
```python
socketio.run(app, host='0.0.0.0', port=5001)  # Change to different port
```

## Performance Tips

1. **GPU Acceleration**: Ensure CUDA is available for faster processing
2. **Reduce Frame Rate**: Process every Nth frame if needed
3. **Optimize Confidence**: Adjust MIN_CONFIDENCE threshold
4. **Network**: Use wired connection for RTSP streams

## Monitoring Multiple Cameras

To add more cameras, edit `enhanced_dashboard.py`:
```python
CAMERAS = {
    'camera_1': {
        'name': 'North Pasture',
        'url': 'your_rtsp_url_here',
        'enabled': True
    },
    'camera_2': {
        'name': 'South Pasture',
        'url': 'another_rtsp_url',
        'enabled': True
    }
    # Add more cameras here
}
```

## Data Export

### Generate Report
Click the "Report" button in the dashboard header to download:
- JSON format analytics report
- Includes all statistics and historical data
- Timestamps and detection counts

### Take Snapshots
Click "Snapshot" under any camera feed to save current frame

## Production Deployment

For production use:
```bash
# Install production server
pip install gunicorn eventlet

# Run with Gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 enhanced_dashboard:app
```

## Support

If you encounter issues:
1. Run `python test_dashboard.py` for diagnostics
2. Check console output for error messages
3. Verify all files exist in correct locations
4. Ensure virtual environment is activated

---

**Ready to monitor bison in real-time!**

Dashboard URL: **http://localhost:5000**
