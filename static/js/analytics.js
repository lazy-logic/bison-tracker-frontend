// BisonGuard Analytics Dashboard JavaScript

// Global variables
const socket = io();
let charts = {};
let heatmapInstances = {};
let currentStats = {};
let cameras = {};

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing BisonGuard Analytics Dashboard...');
    
    // Load dashboard components
    loadDashboardLayout();
    initializeSocketHandlers();
    initializeCharts();
    startPeriodicUpdates();
    
    // Set up tab event listeners
    setupTabEventListeners();
    
    // Update time immediately
    updateCurrentTime();
});

// Load the main dashboard layout
function loadDashboardLayout() {
    const mainContainer = document.getElementById('main-dashboard');
    
    mainContainer.innerHTML = `
        <!-- Key Metrics Row -->
        <div class="row mb-4" id="metrics-row">
            ${createMetricsCards()}
        </div>
        
        <!-- Tab Navigation -->
        <div class="row">
            <div class="col-12">
                ${createTabNavigation()}
                <div class="tab-content" id="tab-content">
                    ${createTabPanes()}
                </div>
            </div>
        </div>
        
        <!-- Alerts Section -->
        <div class="row mt-4">
            <div class="col-12">
                <div class="analytics-card">
                    <h5><i class="fas fa-bell"></i> Recent Alerts</h5>
                    <div id="alerts-container" style="max-height: 300px; overflow-y: auto;">
                        <div class="text-center text-muted py-3">No alerts at this time</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Create metrics cards HTML
function createMetricsCards() {
    const metrics = [
        { id: 'current-count', icon: 'fa-paw', label: 'Current Count', change: 'count-change' },
        { id: 'unique-tracks', icon: 'fa-fingerprint', label: 'Unique Tracks', change: 'tracks-trend' },
        { id: 'peak-count', icon: 'fa-trophy', label: 'Peak Today', change: 'peak-time' },
        { id: 'avg-confidence', icon: 'fa-percentage', label: 'Avg Confidence', change: 'confidence-quality' },
        { id: 'movement-speed', icon: 'fa-running', label: 'Avg Speed', change: null, unit: 'px/sec' },
        { id: 'total-alerts', icon: 'fa-bell', label: 'Alerts Today', change: 'alert-severity' }
    ];
    
    return metrics.map(metric => `
        <div class="col-md-2">
            <div class="stat-card">
                <i class="fas ${metric.icon} fa-2x mb-2" style="opacity: 0.8;"></i>
                <div class="stat-value" id="${metric.id}">0</div>
                <div class="stat-label">${metric.label}</div>
                ${metric.change ? `
                    <div class="stat-change positive">
                        <span id="${metric.change}">--</span>
                    </div>
                ` : metric.unit ? `
                    <div class="stat-change">
                        <span>${metric.unit}</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// Create tab navigation
function createTabNavigation() {
    return `
        <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item">
                <a class="nav-link active" data-bs-toggle="tab" href="#live-view">
                    <i class="fas fa-video"></i> Live View
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#analytics">
                    <i class="fas fa-chart-bar"></i> Analytics
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#heatmap">
                    <i class="fas fa-fire"></i> Activity Heatmap
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#tracking">
                    <i class="fas fa-route"></i> Tracking Paths
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#settings">
                    <i class="fas fa-cog"></i> Settings
                </a>
            </li>
        </ul>
    `;
}

// Create tab panes
function createTabPanes() {
    return `
        <div class="tab-pane fade show active" id="live-view">
            <div class="row" id="camera-feeds">
                <!-- Camera feeds will be loaded here -->
            </div>
        </div>
        
        <div class="tab-pane fade" id="analytics">
            <div class="row">
                <div class="col-md-8">
                    <div class="analytics-card">
                        <h5>Detection Timeline (24 Hours)</h5>
                        <div class="chart-container">
                            <canvas id="timeline-chart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="analytics-card">
                        <h5>Detection Distribution</h5>
                        <div class="chart-container">
                            <canvas id="distribution-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-md-6">
                    <div class="analytics-card">
                        <h5>Confidence Distribution</h5>
                        <div class="chart-container">
                            <canvas id="confidence-chart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="analytics-card">
                        <h5>Movement Patterns</h5>
                        <div class="chart-container">
                            <canvas id="movement-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="tab-pane fade" id="heatmap">
            <div class="row" id="heatmap-containers">
                <!-- Heatmaps will be loaded here -->
            </div>
        </div>
        
        <div class="tab-pane fade" id="tracking">
            <div class="analytics-card">
                <h5>Recent Tracking Paths</h5>
                <div id="tracking-visualization" style="height: 500px; width: 100%; position: relative;">
                    <canvas id="paths-canvas" style="width: 100%; height: 100%; border: 1px solid #ddd; border-radius: 4px;"></canvas>
                </div>
            </div>
        </div>
        
        <div class="tab-pane fade" id="settings">
            ${createSettingsPanel()}
        </div>
    `;
}

// Create settings panel
function createSettingsPanel() {
    return `
        <div class="analytics-card">
            <h5>Alert Thresholds</h5>
            <div class="settings-panel">
                <div class="mb-3">
                    <label>High Activity Threshold: <span id="high-threshold-value">10</span></label>
                    <input type="range" class="threshold-slider" id="high-threshold" 
                           min="5" max="30" value="10" 
                           onchange="updateThreshold('high_activity', this.value)">
                </div>
                <div class="mb-3">
                    <label>Low Confidence Alert: <span id="conf-threshold-value">0.3</span></label>
                    <input type="range" class="threshold-slider" id="conf-threshold" 
                           min="0.1" max="0.5" step="0.05" value="0.3"
                           onchange="updateThreshold('low_confidence', this.value)">
                </div>
                <div class="mb-3">
                    <label>Rapid Movement (px/sec): <span id="movement-threshold-value">50</span></label>
                    <input type="range" class="threshold-slider" id="movement-threshold" 
                           min="20" max="100" value="50"
                           onchange="updateThreshold('rapid_movement', this.value)">
                </div>
            </div>
        </div>
    `;
}

// Setup tab event listeners
function setupTabEventListeners() {
    // Add event listener for tab changes
    document.addEventListener('shown.bs.tab', function (event) {
        const targetId = event.target.getAttribute('href');
        
        if (targetId === '#heatmap') {
            // Load heatmaps when heatmap tab is activated
            setTimeout(loadHeatmaps, 100); // Small delay to ensure DOM is ready
        } else if (targetId === '#tracking') {
            // Load tracking paths when tracking tab is activated
            setTimeout(loadTrackingPaths, 100); // Small delay to ensure DOM is ready
        }
    });
}

// Initialize Socket.IO handlers
function initializeSocketHandlers() {
    socket.on('connect', function() {
        console.log('Connected to BisonGuard Analytics Server');
    });
    
    socket.on('initial_data', function(data) {
        console.log('Received initial data:', data);
        if (data.cameras) {
            loadCameraFeeds(data.cameras);
        }
        if (data.stats) {
            updateStatistics(data.stats);
        }
    });
    
    socket.on('analytics_update', function(data) {
        updateStatistics(data);
        updateCharts(data);
    });
    
    socket.on('frame_processed', function(data) {
        updateCameraStats(data);
    });
    
    socket.on('detection_event', function(data) {
        handleDetectionEvent(data);
    });
    
    socket.on('alert', function(alert) {
        addAlert(alert);
    });
}

// Load camera feeds
function loadCameraFeeds(cameraList) {
    // This function would be called with actual camera data
    // For now, using placeholder
    const feedsContainer = document.getElementById('camera-feeds');
    if (!feedsContainer) return;
    
    const feedsHTML = cameraList.map(cameraId => `
        <div class="col-md-6 mb-3">
            <div class="analytics-card">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5>
                        <i class="fas fa-camera"></i> Camera ${cameraId}
                    </h5>
                    <div>
                        <span class="camera-badge online" id="status-${cameraId}">
                            ONLINE
                        </span>
                        <span class="ms-2" id="fps-${cameraId}">0 FPS</span>
                    </div>
                </div>
                <div class="video-container">
                    <img src="/video_feed/${cameraId}" 
                         class="video-feed" 
                         id="video-${cameraId}"
                         onerror="handleVideoError('${cameraId}')">
                </div>
                <div class="mt-3 d-flex justify-content-between">
                    <span>
                        <i class="fas fa-paw"></i> 
                        <span id="count-${cameraId}">0</span> Bison
                    </span>
                    <span>
                        <i class="fas fa-fingerprint"></i>
                        <span id="tracks-${cameraId}">0</span> Tracks
                    </span>
                    <button class="btn btn-sm btn-outline-light" 
                            onclick="takeSnapshot('${cameraId}')">
                        <i class="fas fa-camera"></i> Snapshot
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    
    feedsContainer.innerHTML = feedsHTML;
}

// Update statistics
function updateStatistics(stats) {
    if (stats.current_count !== undefined) {
        document.getElementById('current-count').textContent = stats.current_count;
    }
    if (stats.unique_tracks !== undefined) {
        document.getElementById('unique-tracks').textContent = stats.unique_tracks;
    }
    if (stats.peak_count !== undefined) {
        document.getElementById('peak-count').textContent = stats.peak_count;
    }
    if (stats.avg_confidence !== undefined) {
        const confidence = Math.round(stats.avg_confidence * 100);
        document.getElementById('avg-confidence').textContent = confidence + '%';
    }
    if (stats.total_alerts !== undefined) {
        document.getElementById('total-alerts').textContent = stats.total_alerts;
    }
    if (stats.movement && stats.movement.avg_speed !== undefined) {
        document.getElementById('movement-speed').textContent = 
            stats.movement.avg_speed.toFixed(1);
    }
    if (stats.peak_time) {
        const time = new Date(stats.peak_time).toLocaleTimeString();
        const peakTimeEl = document.getElementById('peak-time');
        if (peakTimeEl) peakTimeEl.textContent = time;
    }
    
    currentStats = stats;
}

// Update camera stats
function updateCameraStats(data) {
    if (data.camera_id) {
        const countEl = document.getElementById(`count-${data.camera_id}`);
        if (countEl) countEl.textContent = data.detections || 0;
        
        const fpsEl = document.getElementById(`fps-${data.camera_id}`);
        if (fpsEl) fpsEl.textContent = (data.fps || 0).toFixed(1) + ' FPS';
    }
}

// Handle detection events
function handleDetectionEvent(data) {
    console.log('Detection event:', data);
    // Update relevant UI elements
}

// Add alert to the container
function addAlert(alert) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    // Remove placeholder if exists
    const placeholder = alertsContainer.querySelector('.text-center.text-muted');
    if (placeholder) {
        placeholder.remove();
    }
    
    const alertEl = document.createElement('div');
    alertEl.className = `alert-item ${alert.severity || ''}`;
    alertEl.innerHTML = `
        <div class="d-flex justify-content-between">
            <strong>${alert.message}</strong>
            <small>${new Date(alert.timestamp || Date.now()).toLocaleTimeString()}</small>
        </div>
        <small>Camera: ${alert.camera_id || 'Unknown'}</small>
    `;
    
    alertsContainer.insertBefore(alertEl, alertsContainer.firstChild);
    
    // Keep only last 10 alerts
    const alerts = alertsContainer.querySelectorAll('.alert-item');
    if (alerts.length > 10) {
        alerts[alerts.length - 1].remove();
    }
}

// Handle video feed errors
function handleVideoError(cameraId) {
    console.error(`Video feed error for camera ${cameraId}`);
    const statusEl = document.getElementById(`status-${cameraId}`);
    if (statusEl) {
        statusEl.className = 'camera-badge offline';
        statusEl.textContent = 'OFFLINE';
    }
}

// Take snapshot
function takeSnapshot(cameraId) {
    fetch(`/api/camera/${cameraId}/snapshot`)
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bison_snapshot_${cameraId}_${Date.now()}.jpg`;
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Snapshot error:', error);
            alert('Failed to take snapshot');
        });
}

// Update threshold
function updateThreshold(type, value) {
    socket.emit('set_alert_threshold', { type: type, value: parseFloat(value) });
    
    // Update display
    if (type === 'high_activity') {
        document.getElementById('high-threshold-value').textContent = value;
    } else if (type === 'low_confidence') {
        document.getElementById('conf-threshold-value').textContent = value;
    } else if (type === 'rapid_movement') {
        document.getElementById('movement-threshold-value').textContent = value;
    }
}

// Generate report
function generateReport() {
    fetch('/api/analytics/report')
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], 
                                { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bisonguard_report_${Date.now()}.json`;
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Report generation error:', error);
            alert('Failed to generate report');
        });
}

// Update current time
function updateCurrentTime() {
    const now = new Date();
    const timeEl = document.getElementById('current-time');
    if (timeEl) {
        timeEl.textContent = now.toLocaleString();
    }
}

// Start periodic updates
function startPeriodicUpdates() {
    // Update time every second
    setInterval(updateCurrentTime, 1000);
    
    // Fetch analytics data every 5 seconds
    setInterval(() => {
        socket.emit('request_analytics');
    }, 5000);
    
    // Fetch historical data every 30 seconds
    setInterval(fetchHistoricalData, 30000);
}

// Fetch historical data
function fetchHistoricalData() {
    fetch('/api/analytics/historical?hours=24')
        .then(response => response.json())
        .then(data => {
            updateHistoricalCharts(data);
            updateAlerts(data.alerts);
        })
        .catch(error => console.error('Error fetching historical data:', error));
}

// Load and display heatmaps
function loadHeatmaps() {
    const heatmapContainer = document.getElementById('heatmap-containers');
    if (!heatmapContainer) return;

    // Get cameras from the existing feed containers or define default cameras
    const cameras = ['camera_1', 'camera_2'];
    
    heatmapContainer.innerHTML = '';
    
    cameras.forEach(cameraId => {
        const colDiv = document.createElement('div');
        colDiv.className = 'col-md-6 mb-4';
        
        colDiv.innerHTML = `
            <div class="analytics-card">
                <h5>Activity Heatmap - ${cameraId.replace('_', ' ').toUpperCase()}</h5>
                <div id="heatmap-${cameraId}" style="width: 100%; height: 300px; position: relative;">
                    <canvas id="heatmap-canvas-${cameraId}" width="320" height="240" 
                            style="width: 100%; height: 100%; border: 1px solid #ddd; border-radius: 4px;">
                    </canvas>
                    <div id="heatmap-loading-${cameraId}" class="text-center p-4">
                        <i class="fas fa-spinner fa-spin"></i> Loading heatmap...
                    </div>
                </div>
                <div class="mt-2">
                    <small class="text-muted">
                        <i class="fas fa-fire text-danger"></i> High Activity &nbsp;
                        <i class="fas fa-circle text-warning"></i> Medium Activity &nbsp;
                        <i class="fas fa-circle text-info"></i> Low Activity
                    </small>
                </div>
            </div>
        `;
        
        heatmapContainer.appendChild(colDiv);
        
        // Load heatmap data for this camera
        fetchAndRenderHeatmap(cameraId);
    });
}

// Fetch and render heatmap for a specific camera
function fetchAndRenderHeatmap(cameraId) {
    const loadingDiv = document.getElementById(`heatmap-loading-${cameraId}`);
    const canvas = document.getElementById(`heatmap-canvas-${cameraId}`);
    
    if (!canvas) return;
    
    fetch(`/api/analytics/heatmap/${cameraId}`)
        .then(response => response.json())
        .then(data => {
            if (loadingDiv) loadingDiv.style.display = 'none';
            renderHeatmapOnCanvas(canvas, data.heatmap);
        })
        .catch(error => {
            console.error(`Error fetching heatmap for ${cameraId}:`, error);
            if (loadingDiv) {
                loadingDiv.innerHTML = '<i class="fas fa-exclamation-triangle text-warning"></i> Failed to load heatmap';
            }
        });
}

// Render heatmap data on canvas
function renderHeatmapOnCanvas(canvas, heatmapData) {
    if (!canvas || !heatmapData) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Calculate cell dimensions
    const rows = heatmapData.length;
    const cols = heatmapData[0] ? heatmapData[0].length : 0;
    
    if (rows === 0 || cols === 0) {
        // Draw "No Data" message
        ctx.fillStyle = '#666';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No Activity Data', width/2, height/2);
        return;
    }
    
    const cellWidth = width / cols;
    const cellHeight = height / rows;
    
    // Find max value for normalization
    let maxValue = 0;
    for (let i = 0; i < rows; i++) {
        for (let j = 0; j < cols; j++) {
            maxValue = Math.max(maxValue, heatmapData[i][j]);
        }
    }
    
    // Draw heatmap cells
    for (let i = 0; i < rows; i++) {
        for (let j = 0; j < cols; j++) {
            const value = heatmapData[i][j];
            const intensity = maxValue > 0 ? value / maxValue : 0;
            
            if (intensity > 0) {
                // Color mapping: blue (low) -> yellow (medium) -> red (high)
                let r, g, b;
                if (intensity < 0.5) {
                    // Blue to Yellow
                    r = Math.floor(intensity * 2 * 255);
                    g = Math.floor(intensity * 2 * 255);
                    b = Math.floor(255 - intensity * 2 * 255);
                } else {
                    // Yellow to Red
                    r = 255;
                    g = Math.floor(255 - (intensity - 0.5) * 2 * 255);
                    b = 0;
                }
                
                ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.3 + intensity * 0.7})`;
                ctx.fillRect(j * cellWidth, i * cellHeight, cellWidth, cellHeight);
                
                // Add border for visible cells
                ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.8)`;
                ctx.lineWidth = 1;
                ctx.strokeRect(j * cellWidth, i * cellHeight, cellWidth, cellHeight);
            }
        }
    }
    
    // Add grid lines for better visualization
    ctx.strokeStyle = 'rgba(200, 200, 200, 0.3)';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= rows; i++) {
        ctx.beginPath();
        ctx.moveTo(0, i * cellHeight);
        ctx.lineTo(width, i * cellHeight);
        ctx.stroke();
    }
    for (let j = 0; j <= cols; j++) {
        ctx.beginPath();
        ctx.moveTo(j * cellWidth, 0);
        ctx.lineTo(j * cellWidth, height);
        ctx.stroke();
    }
}

// Load and display tracking paths
function loadTrackingPaths() {
    const canvas = document.getElementById('paths-canvas');
    if (!canvas) return;

    // Get the container dimensions
    const container = canvas.parentElement;
    const containerRect = container.getBoundingClientRect();
    
    // Set canvas size to fill container (accounting for DPI)
    const dpr = window.devicePixelRatio || 1;
    canvas.width = (containerRect.width || 800) * dpr;
    canvas.height = (containerRect.height || 500) * dpr;
    
    // Scale the canvas context for high DPI displays
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    
    // Show loading message
    const width = containerRect.width || 800;
    const height = containerRect.height || 500;
    ctx.fillStyle = '#666';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Loading tracking paths...', width/2, height/2);
    
    // Fetch tracking data
    fetch('/api/analytics/tracking_paths?limit=10')
        .then(response => response.json())
        .then(data => {
            renderTrackingPaths(canvas, data, containerRect.width || 800, containerRect.height || 500);
        })
        .catch(error => {
            console.error('Error fetching tracking paths:', error);
            const width = containerRect.width || 800;
            const height = containerRect.height || 500;
            ctx.clearRect(0, 0, width, height);
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Failed to load tracking paths', width/2, height/2);
        });
}

// Render tracking paths on canvas
function renderTrackingPaths(canvas, trackingData, logicalWidth, logicalHeight) {
    if (!canvas || !trackingData) return;
    
    const ctx = canvas.getContext('2d');
    
    // Use logical dimensions for rendering (DPI scaling is handled by context scaling)
    const width = logicalWidth || canvas.offsetWidth || 800;
    const height = logicalHeight || canvas.offsetHeight || 500;
    
    ctx.clearRect(0, 0, width, height);
    
    // Check if we have any tracking data
    const trackIds = Object.keys(trackingData);
    if (trackIds.length === 0) {
        ctx.fillStyle = '#666';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No tracking paths available', width/2, height/2);
        return;
    }
    
    // Calculate bounds for normalization
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    
    trackIds.forEach(trackId => {
        const path = trackingData[trackId];
        if (path && path.length > 0) {
            path.forEach(point => {
                minX = Math.min(minX, point.x);
                maxX = Math.max(maxX, point.x);
                minY = Math.min(minY, point.y);
                maxY = Math.max(maxY, point.y);
            });
        }
    });
    
    // Add padding
    const padding = 50;
    const drawWidth = width - 2 * padding;
    const drawHeight = height - 2 * padding;
    
    // Avoid division by zero
    const xRange = maxX - minX || 1;
    const yRange = maxY - minY || 1;
    
    // Color palette for different tracks
    const colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
        '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
        '#BB8FCE', '#85C1E9', '#82E0AA', '#F8C471'
    ];
    
    // Draw background grid
    ctx.strokeStyle = 'rgba(200, 200, 200, 0.3)';
    ctx.lineWidth = 1;
    
    // Vertical grid lines
    for (let i = 0; i <= 10; i++) {
        const x = padding + (i / 10) * drawWidth;
        ctx.beginPath();
        ctx.moveTo(x, padding);
        ctx.lineTo(x, canvas.height - padding);
        ctx.stroke();
    }
    
    // Horizontal grid lines
    for (let i = 0; i <= 10; i++) {
        const y = padding + (i / 10) * drawHeight;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }
    
    // Draw tracking paths
    trackIds.forEach((trackId, index) => {
        const path = trackingData[trackId];
        if (!path || path.length < 2) return;
        
        const color = colors[index % colors.length];
        
        // Draw path line
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        let isFirstPoint = true;
        path.forEach(point => {
            // Normalize coordinates
            const x = padding + ((point.x - minX) / xRange) * drawWidth;
            const y = padding + ((maxY - point.y) / yRange) * drawHeight; // Flip Y axis
            
            if (isFirstPoint) {
                ctx.moveTo(x, y);
                isFirstPoint = false;
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Draw start point (larger circle)
        const startPoint = path[0];
        const startX = padding + ((startPoint.x - minX) / xRange) * drawWidth;
        const startY = padding + ((maxY - startPoint.y) / yRange) * drawHeight;
        
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(startX, startY, 6, 0, 2 * Math.PI);
        ctx.fill();
        
        // Draw end point (smaller circle with border)
        const endPoint = path[path.length - 1];
        const endX = padding + ((endPoint.x - minX) / xRange) * drawWidth;
        const endY = padding + ((maxY - endPoint.y) / yRange) * drawHeight;
        
        ctx.fillStyle = 'white';
        ctx.beginPath();
        ctx.arc(endX, endY, 4, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(endX, endY, 4, 0, 2 * Math.PI);
        ctx.stroke();
        
        // Add track ID label near start point
        ctx.fillStyle = color;
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';
        ctx.fillText(`Track ${trackId}`, startX + 10, startY - 10);
    });
    
    // Add legend
    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    ctx.textAlign = 'left';
    ctx.fillText('● Start Point', padding, height - 25);
    ctx.fillText('○ End Point', padding + 100, height - 25);
    
    // Add coordinate info
    ctx.textAlign = 'right';
    ctx.fillText(`Tracks: ${trackIds.length}`, width - padding, height - 25);
    ctx.fillText(`Bounds: (${Math.round(minX)}, ${Math.round(minY)}) to (${Math.round(maxX)}, ${Math.round(maxY)})`, width - padding, height - 10);
}

// Update alerts from historical data
function updateAlerts(alerts) {
    if (!alerts || alerts.length === 0) return;
    
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    alertsContainer.innerHTML = '';
    alerts.forEach(alert => addAlert(alert));
}
