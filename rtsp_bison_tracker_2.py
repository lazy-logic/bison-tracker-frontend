#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import cv2
import json
import math
import queue
import shutil
import signal
import threading
import subprocess
import tempfile
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: ultralytics not available. Running in stream-only mode.")

# ─── PARAMETERS ────────────────────────────────────────────────────────────────
DEFAULT_RTSP_URL = "rtsps://cr-14.hostedcloudvideo.com:443/publish-cr/_definst_/XQYKDKIHA6RIQKST9PIKRE77D77547OU9D091HNA/6b55ae911a8dbd2bd7d3a75ae4547acc976d0b9e?action=PLAY"
TRACKER_CFG = "args.yaml"
MODEL_WEIGHTS = "best.pt"
CLASS_NAMES = ["bison"]
MIN_CONFIDENCE = 0.3
HTTP_PORT = 8080
MJPEG_QUALITY = 85
HLS_SEGMENT_TIME = 2         # seconds
HLS_LIST_SIZE = 6            # rolling window size
HLS_DELETE_OLD = True
# ──────────────────────────────────────────────────────────────────────────────


# ─── UTILITIES ────────────────────────────────────────────────────────────────
def which(cmd: str) -> bool:
    """Return True if executable is on PATH."""
    return shutil.which(cmd) is not None


# ─── HLS MANAGER (FFMPEG PIPELINE) ────────────────────────────────────────────
class HLSManager:
    """
    Manages an ffmpeg process that consumes raw frames via stdin
    and emits an HLS playlist + TS segments into a temporary directory.
    """
    def __init__(self, width: int, height: int, fps: float, segment_time=2, list_size=6, delete_old=True):
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps) if fps and not math.isnan(fps) else 25.0
        self.segment_time = int(segment_time)
        self.list_size = int(list_size)
        self.delete_old = bool(delete_old)

        self.enabled = which("ffmpeg")
        self.proc = None
        self.tmpdir = None
        self.playlist_name = "index.m3u8"
        self.segment_pattern = "segment%05d.ts"
        self.stdin_lock = threading.Lock()

        # frame queue & writer thread (to decouple capture pace from ffmpeg pacing)
        self.frame_q = queue.Queue(maxsize=60)  # small buffer to avoid memory growth
        self.writer_thread = None
        self.running = False

    def start(self):
        if not self.enabled:
            print("HLS disabled: ffmpeg not found on PATH.")
            return False

        self.tmpdir = tempfile.mkdtemp(prefix="hls_")
        playlist_path = os.path.join(self.tmpdir, self.playlist_name)
        segment_path = os.path.join(self.tmpdir, self.segment_pattern)

        # Build ffmpeg command
        # Read raw BGR frames from stdin, encode H.264, output HLS.
        cmd = [
            "ffmpeg",
            "-hide_banner", "-loglevel", "error",
            "-y",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s:v", f"{self.width}x{self.height}",
            "-r", f"{self.fps}",
            "-i", "-",                     # stdin
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-pix_fmt", "yuv420p",
            "-f", "hls",
            "-hls_time", str(self.segment_time),
            "-hls_list_size", str(self.list_size),
            "-hls_flags", "delete_segments+independent_segments" if self.delete_old else "independent_segments",
            "-hls_segment_filename", segment_path,
            playlist_path
        ]

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0
            )
        except Exception as e:
            print(f"Failed to start ffmpeg for HLS: {e}")
            self.enabled = False
            return False

        self.running = True
        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.writer_thread.start()
        print(f"HLS started. Serving from: {self.tmpdir}")
        return True

    def _writer_loop(self):
        while self.running and self.proc and (self.proc.poll() is None):
            try:
                frame = self.frame_q.get(timeout=0.3)
            except queue.Empty:
                continue

            try:
                # Write raw frame bytes (BGR24)
                with self.stdin_lock:
                    if self.proc and self.proc.stdin and (self.proc.poll() is None):
                        self.proc.stdin.write(frame.tobytes())
            except Exception as e:
                # If ffmpeg died or write failed, stop gracefully
                print(f"HLS writer error: {e}")
                break

        self._close_proc()

    def write_frame(self, frame):
        """Queue a frame for HLS. Frame must be (H, W, 3) BGR np.uint8."""
        if not self.enabled or not self.running:
            return
        # Drop if queue is full (avoid blocking capture loop)
        try:
            self.frame_q.put_nowait(frame)
        except queue.Full:
            # Drop frame silently
            pass

    def get_playlist_path(self):
        if self.tmpdir:
            return os.path.join(self.tmpdir, self.playlist_name)
        return None

    def resolve_path(self, name):
        """Resolve a requested file within the HLS tmpdir safely."""
        if not self.tmpdir:
            return None
        candidate = os.path.normpath(os.path.join(self.tmpdir, name))
        if os.path.commonprefix([candidate, self.tmpdir]) != self.tmpdir:
            return None
        return candidate

    def stop(self):
        self.running = False
        # Drain queue quickly
        while not self.frame_q.empty():
            try:
                self.frame_q.get_nowait()
            except queue.Empty:
                break
        self._close_proc()
        if self.tmpdir and os.path.isdir(self.tmpdir):
            try:
                shutil.rmtree(self.tmpdir, ignore_errors=True)
            except Exception:
                pass
        self.tmpdir = None

    def _close_proc(self):
        if self.proc:
            try:
                if self.proc.stdin:
                    try:
                        self.proc.stdin.flush()
                    except Exception:
                        pass
                    try:
                        self.proc.stdin.close()
                    except Exception:
                        pass
                # Give ffmpeg a moment to flush
                for _ in range(5):
                    if self.proc.poll() is not None:
                        break
                    time.sleep(0.05)
                if self.proc.poll() is None:
                    try:
                        self.proc.terminate()
                    except Exception:
                        pass
                for _ in range(10):
                    if self.proc.poll() is not None:
                        break
                    time.sleep(0.05)
                if self.proc.poll() is None:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
            finally:
                self.proc = None


# ─── STREAM MANAGER ───────────────────────────────────────────────────────────
class StreamManager:
    def __init__(self, rtsp_url, apply_model=False):
        self.rtsp_url = rtsp_url
        self.apply_model = apply_model
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.model = None
        self.cap = None
        self.hls = None
        self.stream_thread = None

        self.stats = {
            'total_frames': 0,
            'total_detections': 0,
            'max_bison_in_frame': 0,
            'avg_confidence': 0.0,
            'fps': 0.0
        }

        if apply_model and YOLO_AVAILABLE:
            try:
                print(f"Loading YOLO model: {MODEL_WEIGHTS}")
                self.model = YOLO(MODEL_WEIGHTS)
                print("Model loaded successfully")
            except Exception as e:
                print(f"Failed to load model: {e}")
                self.apply_model = False
        elif apply_model and not YOLO_AVAILABLE:
            print("YOLO not available, running without model")
            self.apply_model = False

    def start_stream(self):
        print(f"Connecting to RTSP stream: {self.rtsp_url}")
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot connect to RTSP stream: {self.rtsp_url}")

        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if not fps or math.isnan(fps) or fps <= 1:
            fps = 25.0

        print("Stream properties:")
        print(f"  Resolution: {width}x{height}")
        print(f"  FPS: {fps:.1f}")

        # Start HLS manager (if ffmpeg available)
        self.hls = HLSManager(width, height, fps, HLS_SEGMENT_TIME, HLS_LIST_SIZE, HLS_DELETE_OLD)
        hls_ok = self.hls.start()

        self.running = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

        return width, height, fps, hls_ok

    def _stream_loop(self):
        frame_count = 0
        last_fps_time = time.time()
        fps_frame_count = 0

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to read frame, attempting to reconnect...")
                self.cap.release()
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.rtsp_url)
                continue

            frame_count += 1
            fps_frame_count += 1

            # FPS calc
            now = time.time()
            if now - last_fps_time >= 1.0:
                self.stats['fps'] = fps_frame_count / (now - last_fps_time)
                fps_frame_count = 0
                last_fps_time = now

            # AI processing (optional)
            if self.apply_model and self.model:
                frame = self._process_frame_with_model(frame, frame_count)
            else:
                self._add_basic_overlay(frame, frame_count)

            # Make a copy for MJPEG
            with self.frame_lock:
                self.current_frame = frame.copy()

            # Push to HLS if active
            if self.hls and self.hls.enabled:
                # Important: HLS expects contiguous frames at roughly constant size/rate
                # We queue the current BGR frame
                self.hls.write_frame(frame)

            self.stats['total_frames'] = frame_count

            # Small chill to avoid tight loop
            time.sleep(0.001)

    def _process_frame_with_model(self, frame, frame_count):
        try:
            results = self.model.track(
                source=frame,
                tracker=TRACKER_CFG if os.path.exists(TRACKER_CFG) else "bytetrack.yaml",
                conf=MIN_CONFIDENCE,
                persist=True,
                verbose=False
            )[0]

            boxes = results.boxes
            bison_count = 0
            frame_confidences = []

            if boxes is not None:
                coords = boxes.xyxy.tolist()
                cls_list = boxes.cls.tolist()
                ids_tensor = boxes.id
                id_list = ids_tensor.tolist() if ids_tensor is not None else [None]*len(cls_list)
                conf_list = boxes.conf.tolist()

                for (x1, y1, x2, y2), tid, cls, conf in zip(coords, id_list, cls_list, conf_list):
                    cls = int(cls)
                    if cls >= len(CLASS_NAMES) or CLASS_NAMES[cls] != "bison":
                        continue
                    bison_count += 1
                    frame_confidences.append(conf)
                    x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))

                    color_intensity = int(255 * max(0.0, min(1.0, float(conf))))
                    box_color = (0, color_intensity, 255 - color_intensity)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

                    label = f"ID {int(tid)} ({conf:.3f})" if tid is not None else f"Bison ({conf:.3f})"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                                  (x1 + label_size[0], y1), box_color, -1)
                    cv2.putText(frame, label, (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            self.stats['total_detections'] += bison_count
            self.stats['max_bison_in_frame'] = max(self.stats['max_bison_in_frame'], bison_count)
            if frame_confidences:
                self.stats['avg_confidence'] = sum(frame_confidences) / len(frame_confidences)

            self._add_detection_overlay(frame, bison_count, frame_count)
        except Exception as e:
            print(f"Error in model processing: {e}")
            self._add_basic_overlay(frame, frame_count)
        return frame

    def _add_detection_overlay(self, frame, bison_count, frame_count):
        h, w = frame.shape[:2]
        cv2.putText(frame, f"Bison Count: {bison_count}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        cv2.putText(frame, f"Avg Conf: {self.stats['avg_confidence']:.3f}",
                    (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
        cv2.putText(frame, f"Max Count: {self.stats['max_bison_in_frame']}",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.putText(frame, f"FPS: {self.stats['fps']:.1f}",
                    (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(frame, f"Frame: {frame_count}",
                    (w - 140, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    def _add_basic_overlay(self, frame, frame_count):
        h, w = frame.shape[:2]
        cv2.putText(frame, "Live Stream (No AI Processing)" if not self.apply_model else "Live Stream",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(frame, f"FPS: {self.stats['fps']:.1f}",
                    (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(frame, f"Frame: {frame_count}",
                    (w - 140, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    def get_current_frame(self):
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def stop(self):
        self.running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
        if self.hls:
            try:
                self.hls.stop()
            except Exception:
                pass


# ─── HTTP HANDLER ─────────────────────────────────────────────────────────────
class StreamingHandler(BaseHTTPRequestHandler):
    def __init__(self, stream_manager: StreamManager, *args, **kwargs):
        self.stream_manager = stream_manager
        super().__init__(*args, **kwargs)

    # Content-type helper
    def _ctype(self, path):
        if path.endswith(".m3u8"):
            return "application/vnd.apple.mpegurl"
        if path.endswith(".ts"):
            return "video/mp2t"
        if path.endswith(".mp4"):
            return "video/mp4"
        if path.endswith(".json"):
            return "application/json"
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            return "image/jpeg"
        return "application/octet-stream"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            return self.serve_main_page()
        elif parsed.path == '/mjpeg':
            return self.serve_mjpeg_stream()
        elif parsed.path == '/stats':
            return self.serve_stats()
        elif parsed.path == '/hls.m3u8':
            return self.serve_hls_playlist()
        elif parsed.path.startswith('/hls/'):
            # Serve any HLS artifact under /hls/
            name = parsed.path[len('/hls/'):].strip('/')
            return self.serve_hls_file(name)
        else:
            self.send_error(404)

    def serve_main_page(self):
        html_content = self.generate_html_player()
        data = html_content.encode("utf-8")
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_mjpeg_stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

        try:
            while self.stream_manager.running:
                frame = self.stream_manager.get_current_frame()
                if frame is not None:
                    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY])
                    if not ok:
                        time.sleep(0.01)
                        continue
                    frame_bytes = buf.tobytes()

                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(frame_bytes)))
                    self.end_headers()
                    self.wfile.write(frame_bytes)
                    self.wfile.write(b'\r\n')
                time.sleep(1/30)
        except Exception as e:
            print(f"MJPEG streaming error: {e}")

    def serve_stats(self):
        stats = self.stream_manager.stats.copy()
        stats_json = json.dumps(stats, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(stats_json)))
        self.end_headers()
        self.wfile.write(stats_json)

    def serve_hls_playlist(self):
        """Serve the HLS master playlist path if available, else 503."""
        hls = self.stream_manager.hls
        if not hls or not hls.enabled:
            self.send_response(503)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"HLS not available (ffmpeg not found or failed to start).")
            return

        playlist = hls.get_playlist_path()
        if not playlist or not os.path.exists(playlist):
            # Playlist not ready yet
            self.send_response(202)  # Accepted, not ready
            self.send_header('Retry-After', '1')
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"Playlist not ready. Try again shortly.")
            return

        with open(playlist, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_hls_file(self, name: str):
        hls = self.stream_manager.hls
        if not hls or not hls.enabled:
            self.send_error(404)
            return
        path = hls.resolve_path(name)
        if not path or not os.path.exists(path):
            self.send_error(404)
            return
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', self._ctype(path))
            # Small cache for segments; playlist should be no-cache
            if path.endswith(".ts"):
                self.send_header('Cache-Control', 'public, max-age=60')
            else:
                self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_error(500)

    def generate_html_player(self):
        model_status = "ON" if self.stream_manager.apply_model else "OFF"
        hls_available = bool(self.stream_manager.hls and self.stream_manager.hls.enabled)

        # No emojis; simple badges instead
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Bison Tracker Live Stream</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        :root {{
            --bg: #0f1115; --panel:#161a22; --muted:#8b98a5; --text:#e6edf3; --brand:#579aff; --ok:#4ade80; --warn:#fbbf24; --err:#ef4444;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0; padding: 20px; background: var(--bg); color: var(--text);
            font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,Helvetica,sans-serif;
        }}
        .header {{
            display:flex; align-items:center; justify-content:space-between;
            background: linear-gradient(135deg, #334155 0%, #111827 100%);
            border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;
        }}
        .title {{ font-size: 20px; font-weight: 700; letter-spacing: .3px; }}
        .badges {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
        .badge {{ font-size:12px; padding:4px 8px; border-radius:999px; background:#263041; color:#c6d4e1; border:1px solid #2c3a4f; }}
        .badge.ok {{ color:#052e16; background:#bbf7d0; border-color:#86efac; }}
        .badge.warn {{ color:#3a2202; background:#fde68a; border-color:#fcd34d; }}
        .badge.err {{ color:#450a0a; background:#fecaca; border-color:#fca5a5; }}
        .grid {{ display:flex; gap:20px; flex-wrap:wrap; }}
        .card {{
            flex:1; min-width: 320px; background: var(--panel); border:1px solid #1f2530;
            border-radius: 12px; padding: 16px;
        }}
        .card h3 {{ margin:0 0 12px; font-size:16px; color:#a3cef1; }}
        video, img {{ width:100%; max-width: 720px; height:auto; border-radius: 8px; background:#000; }}
        .controls {{ display:flex; gap:10px; flex-wrap:wrap; margin:18px 0; }}
        button {{
            padding: 10px 14px; border:1px solid #2b3749; background:#1b2431; color:var(--text);
            border-radius: 8px; cursor:pointer; font-size:14px;
        }}
        button:hover {{ background:#202b3a; }}
        .stats {{ margin-top: 10px; }}
        .stats-grid {{
            display:grid; grid-template-columns: repeat(auto-fit, minmax(160px,1fr));
            gap:12px; margin-top:10px;
        }}
        .stat {{ background:#121720; border:1px solid #202839; border-radius:8px; padding:10px; }}
        .stat .val {{ font-weight:700; font-size:20px; color:#c7f9cc; }}
        .stat .lbl {{ font-size:12px; color:var(--muted); margin-top:4px; }}
        .note {{ font-size:12px; color:var(--muted); margin-top:6px; }}
        .error {{ color: var(--err); font-size: 13px; margin-top: 8px; }}
        code {{ background:#0b0e14; border:1px solid #1b2130; padding:2px 6px; border-radius:6px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">Bison Tracker Live Stream</div>
        <div class="badges">
            <span class="badge">AI Processing: <strong>{model_status}</strong></span>
            <span class="badge">RTSP Source</span>
            <span class="badge {'ok' if hls_available else 'warn'}">HLS: {'Ready' if hls_available else 'Initializing / Requires ffmpeg'}</span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>MJPEG Stream</h3>
            <img id="mjpeg" src="/mjpeg" alt="MJPEG Stream"
                 onerror="document.getElementById('mjpeg_err').style.display='block'; this.style.display='none';">
            <div id="mjpeg_err" class="error" style="display:none;">MJPEG stream unavailable.</div>

            <div class="controls">
                <button onclick="refreshMjpeg()">Refresh MJPEG</button>
                <button onclick="toggleFullscreen('mjpeg')">Fullscreen</button>
            </div>
            <div class="note">MJPEG is simple and widely compatible, but uses more bandwidth.</div>
        </div>

        <div class="card">
            <h3>HLS Stream</h3>
            <video id="hlsVideo" controls autoplay muted playsinline></video>
            <div id="hls_err" class="error" style="display:none;">HLS not available yet. If it persists, ensure <code>ffmpeg</code> is installed.</div>
            <div class="controls">
                <button onclick="toggleFullscreen('hlsVideo')">Fullscreen</button>
            </div>
            <div class="note">HLS provides adaptive, chunked HTTP streaming; good for browsers and scale-out delivery.</div>
        </div>
    </div>

    <div class="card stats">
        <h3>Live Statistics</h3>
        <div class="stats-grid">
            <div class="stat"><div class="val" id="total-frames">0</div><div class="lbl">Total Frames</div></div>
            <div class="stat"><div class="val" id="fps">0.0</div><div class="lbl">FPS</div></div>
            <div class="stat"><div class="val" id="total-detections">0</div><div class="lbl">Total Detections</div></div>
            <div class="stat"><div class="val" id="max-bison">0</div><div class="lbl">Max Bison / Frame</div></div>
            <div class="stat"><div class="val" id="avg-confidence">0.000</div><div class="lbl">Avg Confidence</div></div>
        </div>
    </div>

<script>
function refreshMjpeg() {{
    const img = document.getElementById('mjpeg');
    const src = img.src;
    img.src = '';
    setTimeout(() => img.src = src, 100);
}}

function toggleFullscreen(id) {{
    const el = document.getElementById(id);
    if (!el) return;
    if (el.requestFullscreen) el.requestFullscreen();
}}

// Stats updater
function updateStats() {{
    fetch('/stats')
      .then(r => r.json())
      .then(d => {{
        document.getElementById('total-frames').textContent = Number(d.total_frames||0).toLocaleString();
        document.getElementById('fps').textContent = (Number(d.fps)||0).toFixed(1);
        document.getElementById('total-detections').textContent = Number(d.total_detections||0).toLocaleString();
        document.getElementById('max-bison').textContent = Number(d.max_bison_in_frame||0);
        document.getElementById('avg-confidence').textContent = (Number(d.avg_confidence)||0).toFixed(3);
      }})
      .catch(()=>{{}});
}}
setInterval(updateStats, 2000);
updateStats();

// HLS setup with retry
const video = document.getElementById('hlsVideo');
function tryLoadHls() {{
    fetch('/hls.m3u8', {{ cache: 'no-store' }})
      .then(resp => {{
        if (resp.status === 200) return '/hls.m3u8';
        throw new Error('Playlist not ready');
      }})
      .then(url => {{
        if (window.Hls && Hls.isSupported()) {{
            const hls = new Hls({{liveDurationInfinity: true}});
            hls.loadSource(url);
            hls.attachMedia(video);
            hls.on(Hls.Events.ERROR, function(e, data) {{
                document.getElementById('hls_err').style.display='block';
            }});
        }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
            video.src = url;
        }} else {{
            document.getElementById('hls_err').style.display='block';
        }}
      }})
      .catch(() => {{
        document.getElementById('hls_err').style.display='block';
      }});
}}
setTimeout(tryLoadHls, 800); // small delay for ffmpeg to start
</script>
</body>
</html>"""

    def log_message(self, format, *args):
        # Silence default logging
        pass


def create_handler(stream_manager):
    class Handler(StreamingHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(stream_manager, *args, **kwargs)
    return Handler


def signal_handler(signum, frame):
    print("\nShutting down...")
    global server, stream_manager
    try:
        if 'stream_manager' in globals() and stream_manager:
            stream_manager.stop()
    except Exception:
        pass
    try:
        if 'server' in globals() and server:
            server.shutdown()
    except Exception:
        pass
    sys.exit(0)


def get_user_input():
    print("Bison Tracker RTSP Stream Setup")
    print("=" * 50)
    rtsp_url = input(f"Enter RTSP URL (default: {DEFAULT_RTSP_URL}): ").strip() or DEFAULT_RTSP_URL

    if YOLO_AVAILABLE:
        print("\nAI Processing Options:")
        print("1. Apply bison detection model (requires model files)")
        print("2. Stream only (no AI processing)")
        while True:
            choice = input("Choose option (1 or 2): ").strip()
            if choice == "1":
                apply_model = True
                break
            if choice == "2":
                apply_model = False
                break
            print("Please enter 1 or 2")
    else:
        print("\nYOLO not available, will stream without AI processing")
        apply_model = False

    return rtsp_url, apply_model


def main():
    global server, stream_manager

    signal.signal(signal.SIGINT, signal_handler)

    print("RTSP Bison Tracker Streaming Server")
    print("=" * 60)

    rtsp_url, apply_model = get_user_input()

    print("\nInitializing stream manager...")
    stream_manager = StreamManager(rtsp_url, apply_model)

    try:
        width, height, fps, hls_ok = stream_manager.start_stream()
        print("✅ Stream started")
        if hls_ok:
            print("✅ HLS pipeline ready (ffmpeg)")
        else:
            print("⚠️  HLS disabled (ffmpeg not found or failed to start)")

        handler = create_handler(stream_manager)
        server = HTTPServer(('localhost', HTTP_PORT), handler)

        print(f"\nStarting web server on port {HTTP_PORT}")
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        url = f"http://localhost:{HTTP_PORT}"
        print(f"\nServer running:")
        print(f"  Main page:   {url}")
        print(f"  MJPEG:       {url}/mjpeg")
        print(f"  HLS:         {url}/hls.m3u8  (segments under /hls/...)")
        print(f"  Statistics:  {url}/stats\n")

        try:
            webbrowser.open(url)
        except Exception:
            pass

        print("=" * 60)
        print("Press Ctrl+C to stop.")
        print("=" * 60)

        # Keep alive
        while True:
            time.sleep(1)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("\nCleaning up...")
        if stream_manager:
            stream_manager.stop()
        if 'server' in globals():
            try:
                server.shutdown()
            except Exception:
                pass
        print("Done.")


if __name__ == "__main__":
    main()
