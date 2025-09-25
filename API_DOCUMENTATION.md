# BisonGuard API Documentation

## Overview
The BisonGuard system provides a comprehensive RESTful API and WebSocket interface for real-time bison detection, tracking, and behavior analysis. This document details all available endpoints, data formats, and integration methods.

## Base URL
```
http://localhost:5000
```

## Authentication
Currently, the API does not require authentication for local development. Production deployment should implement API key or OAuth2 authentication.

## WebSocket Connection
```javascript
const socket = io('http://localhost:5000');
```

---

## REST API Endpoints

### 1. Detection & Tracking

#### GET /api/detections
Retrieve current detection data from all active cameras.

**Response:**
```json
{
  "timestamp": "2024-01-25T14:30:00Z",
  "cameras": {
    "camera_1": {
      "count": 12,
      "detections": [
        {
          "id": 1,
          "bbox": [100, 200, 150, 180],
          "confidence": 0.92,
          "track_id": "bison_001"
        }
      ],
      "fps": 25.3
    }
  },
  "total_count": 12
}
```

#### GET /api/detections/history
Retrieve historical detection data.

**Query Parameters:**
- `start_time` (ISO 8601 format): Start of time range
- `end_time` (ISO 8601 format): End of time range
- `camera_id` (optional): Specific camera ID
- `limit` (optional, default: 100): Maximum number of records

**Response:**
```json
{
  "data": [
    {
      "timestamp": "2024-01-25T14:00:00Z",
      "camera_id": "camera_1",
      "count": 8,
      "average_confidence": 0.87
    }
  ],
  "total_records": 150,
  "time_range": {
    "start": "2024-01-25T00:00:00Z",
    "end": "2024-01-25T14:30:00Z"
  }
}
```

### 2. Analytics

#### GET /api/analytics/behavior
Get current behavior analysis for detected bison.

**Response:**
```json
{
  "timestamp": "2024-01-25T14:30:00Z",
  "behaviors": {
    "grazing": 65,
    "moving": 20,
    "resting": 10,
    "alert": 3,
    "unknown": 2
  },
  "dominant_behavior": "grazing",
  "confidence": 0.89
}
```

#### GET /api/analytics/movement
Get movement pattern analysis.

**Response:**
```json
{
  "average_speed": 1.2,
  "max_speed": 4.5,
  "direction_changes": 12,
  "distance_traveled": 234.5,
  "movement_patterns": [
    {
      "pattern": "circular",
      "confidence": 0.75,
      "duration_minutes": 15
    }
  ]
}
```

#### GET /api/analytics/herd
Get herd dynamics analysis.

**Response:**
```json
{
  "herd_cohesion": 78.5,
  "clusters": [
    {
      "id": 1,
      "size": 8,
      "center": {"x": 450, "y": 320},
      "radius": 50
    }
  ],
  "total_groups": 2,
  "average_group_size": 6
}
```

#### GET /api/analytics/statistics
Get comprehensive statistics.

**Query Parameters:**
- `period` (optional): "hour", "day", "week", "month"
- `metric` (optional): Specific metric to retrieve

**Response:**
```json
{
  "period": "day",
  "statistics": {
    "total_detections": 1250,
    "unique_individuals": 15,
    "peak_count": 18,
    "average_count": 12.3,
    "total_alerts": 5,
    "uptime_percentage": 99.8
  },
  "trends": {
    "detection_trend": "increasing",
    "activity_trend": "stable"
  }
}
```

### 3. Camera Management

#### GET /api/cameras
List all configured cameras.

**Response:**
```json
{
  "cameras": [
    {
      "id": "camera_1",
      "name": "North Pasture",
      "status": "active",
      "url": "rtsp://...",
      "resolution": "1920x1080",
      "fps": 30,
      "ai_enabled": true
    }
  ]
}
```

#### POST /api/cameras/{camera_id}/control
Control camera settings.

**Request Body:**
```json
{
  "action": "toggle_ai",
  "parameters": {
    "enabled": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "camera_id": "camera_1",
  "new_state": {
    "ai_enabled": true
  }
}
```

### 4. Alerts & Notifications

#### GET /api/alerts
Get recent alerts.

**Query Parameters:**
- `severity` (optional): "low", "medium", "high"
- `limit` (optional, default: 50)

**Response:**
```json
{
  "alerts": [
    {
      "id": "alert_001",
      "timestamp": "2024-01-25T14:25:00Z",
      "severity": "high",
      "type": "rapid_movement",
      "message": "Rapid movement detected in North Pasture",
      "data": {
        "speed": 6.2,
        "location": {"x": 500, "y": 300}
      }
    }
  ]
}
```

#### POST /api/alerts/acknowledge/{alert_id}
Acknowledge an alert.

**Response:**
```json
{
  "success": true,
  "alert_id": "alert_001",
  "acknowledged_at": "2024-01-25T14:30:00Z"
}
```

### 5. Video Streaming

#### GET /video_feed/{camera_id}
Get MJPEG video stream from a specific camera.

**Response:**
- Content-Type: multipart/x-mixed-replace
- Returns continuous JPEG frames

#### GET /hls/{camera_id}/playlist.m3u8
Get HLS playlist for adaptive streaming.

**Response:**
- Content-Type: application/vnd.apple.mpegurl
- Returns HLS playlist

### 6. Data Export

#### GET /api/export/csv
Export data in CSV format.

**Query Parameters:**
- `data_type`: "detections", "analytics", "alerts"
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)

**Response:**
- Content-Type: text/csv
- Returns CSV file download

#### GET /api/export/json
Export data in JSON format.

**Query Parameters:**
- Same as CSV export

**Response:**
- Content-Type: application/json
- Returns JSON file download

---

## WebSocket Events

### Client to Server Events

#### join
Join a specific room for targeted updates.
```javascript
socket.emit('join', { room: 'camera_1' });
```

#### request_update
Request immediate data update.
```javascript
socket.emit('request_update', { type: 'detections' });
```

### Server to Client Events

#### detection_update
Real-time detection updates.
```javascript
socket.on('detection_update', (data) => {
  console.log('New detection:', data);
  // data = { camera_id, count, positions, confidence, timestamp }
});
```

#### tracking_update
Real-time tracking updates.
```javascript
socket.on('tracking_update', (data) => {
  console.log('Tracking update:', data);
  // data = { tracks: [{id, position, velocity}], timestamp }
});
```

#### analytics_update
Real-time analytics updates.
```javascript
socket.on('analytics_update', (data) => {
  console.log('Analytics:', data);
  // data = { behavior, movement, herd_dynamics, timestamp }
});
```

#### alert
Real-time alert notifications.
```javascript
socket.on('alert', (data) => {
  console.log('Alert:', data);
  // data = { severity, message, type, data, timestamp }
});
```

#### status_update
System status updates.
```javascript
socket.on('status_update', (data) => {
  console.log('Status:', data);
  // data = { cameras, system_health, timestamp }
});
```

---

## Data Models

### Detection Object
```typescript
interface Detection {
  id: number;
  bbox: [number, number, number, number]; // [x, y, width, height]
  confidence: number;
  track_id?: string;
  timestamp: string;
  camera_id: string;
}
```

### Track Object
```typescript
interface Track {
  id: string;
  position: {
    x: number;
    y: number;
  };
  velocity?: {
    magnitude: number;
    direction: number; // degrees
  };
  history: Position[];
  age: number; // frames
}
```

### Behavior Object
```typescript
interface Behavior {
  type: 'grazing' | 'moving' | 'resting' | 'alert' | 'unknown';
  confidence: number;
  duration: number; // seconds
  bison_id?: string;
}
```

### Alert Object
```typescript
interface Alert {
  id: string;
  severity: 'low' | 'medium' | 'high';
  type: string;
  message: string;
  timestamp: string;
  data: any;
  acknowledged: boolean;
}
```

---

## Error Handling

All API endpoints return consistent error responses:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  },
  "timestamp": "2024-01-25T14:30:00Z"
}
```

### Common Error Codes
- `CAMERA_NOT_FOUND`: Specified camera ID does not exist
- `INVALID_PARAMETERS`: Request parameters are invalid
- `STREAM_UNAVAILABLE`: Video stream is temporarily unavailable
- `PROCESSING_ERROR`: Error in AI processing pipeline
- `DATABASE_ERROR`: Database operation failed

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- REST API: 100 requests per minute per IP
- WebSocket: 50 messages per minute per connection
- Video streams: 5 concurrent streams per IP

---

## Integration Examples

### JavaScript/React
```javascript
// Fetch current detections
async function getCurrentDetections() {
  const response = await fetch('http://localhost:5000/api/detections');
  const data = await response.json();
  return data;
}

// Connect to WebSocket for real-time updates
const socket = io('http://localhost:5000');

socket.on('connect', () => {
  console.log('Connected to BisonGuard');
  socket.emit('join', { room: 'analytics' });
});

socket.on('detection_update', (data) => {
  updateUI(data);
});
```

### Python
```python
import requests
import socketio

# REST API example
response = requests.get('http://localhost:5000/api/detections')
detections = response.json()

# WebSocket example
sio = socketio.Client()

@sio.on('detection_update')
def on_detection(data):
    print(f"New detection: {data}")

sio.connect('http://localhost:5000')
```

### cURL
```bash
# Get current detections
curl http://localhost:5000/api/detections

# Get behavior analytics
curl http://localhost:5000/api/analytics/behavior

# Export data as CSV
curl "http://localhost:5000/api/export/csv?data_type=detections&start_date=2024-01-01&end_date=2024-01-25" -o detections.csv
```

---

## Performance Considerations

1. **Caching**: Frequently accessed data is cached for 5 seconds
2. **Pagination**: Large datasets are paginated (default: 100 items per page)
3. **Compression**: Responses are gzip compressed
4. **Connection Pooling**: Database connections are pooled for efficiency
5. **Async Processing**: Heavy computations are processed asynchronously

---

## Versioning

The API uses URL versioning. Current version: v1

Future versions will be accessible at:
```
http://localhost:5000/api/v2/...
```

---

## Support

For API support and questions:
- GitHub Issues: [github.com/yourusername/bisonguard/issues](https://github.com/yourusername/bisonguard/issues)
- Documentation: [github.com/yourusername/bisonguard/wiki](https://github.com/yourusername/bisonguard/wiki)
- Email: support@bisonguard.example.com
