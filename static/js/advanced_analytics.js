/**
 * Advanced Analytics Module for BisonGuard
 * Implements comprehensive bison behavior analytics and visualizations
 */

class BisonBehaviorAnalytics {
    constructor() {
        this.socket = io();
        this.detectionHistory = [];
        this.movementPatterns = new Map();
        this.herdDynamics = [];
        this.alertThresholds = {
            rapidMovement: 5.0,  // meters/second
            crowding: 10,        // bison in proximity
            unusualActivity: 2.0 // standard deviations
        };
        
        this.initializeCharts();
        this.setupRealtimeUpdates();
        this.initializeHeatmap();
    }

    initializeCharts() {
        // Movement Pattern Analysis Chart
        this.movementChart = new Chart(document.getElementById('movementPatternChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Average Speed (m/s)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.4
                }, {
                    label: 'Direction Changes',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Speed (m/s)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Direction Changes'
                        },
                        grid: {
                            drawOnChartArea: false,
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Bison Movement Patterns Analysis'
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                return this.analyzeBehavior(context.parsed.y);
                            }.bind(this)
                        }
                    }
                }
            }
        });

        // Herd Dynamics Visualization
        this.herdChart = new Chart(document.getElementById('herdDynamicsChart'), {
            type: 'bubble',
            data: {
                datasets: [{
                    label: 'Herd Clusters',
                    data: [],
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'X Position (meters)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Y Position (meters)'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Herd Spatial Distribution'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Cluster Size: ${context.raw.r} bison`;
                            }
                        }
                    }
                }
            }
        });

        // Behavior Classification Pie Chart
        this.behaviorChart = new Chart(document.getElementById('behaviorChart'), {
            type: 'doughnut',
            data: {
                labels: ['Grazing', 'Moving', 'Resting', 'Alert', 'Unknown'],
                datasets: [{
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Current Behavior Distribution'
                    },
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // Time-based Activity Pattern
        this.activityChart = new Chart(document.getElementById('activityPatternChart'), {
            type: 'bar',
            data: {
                labels: this.generateHourLabels(),
                datasets: [{
                    label: 'Average Activity Level',
                    data: new Array(24).fill(0),
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Activity Level'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: '24-Hour Activity Pattern'
                    }
                }
            }
        });
    }

    initializeHeatmap() {
        // Create heatmap instance for movement density
        const heatmapContainer = document.getElementById('movementHeatmap');
        if (heatmapContainer) {
            this.heatmapInstance = h337.create({
                container: heatmapContainer,
                radius: 40,
                maxOpacity: 0.8,
                minOpacity: 0.1,
                blur: 0.75,
                gradient: {
                    0.0: 'blue',
                    0.25: 'cyan',
                    0.5: 'green',
                    0.75: 'yellow',
                    1.0: 'red'
                }
            });
        }
    }

    setupRealtimeUpdates() {
        // WebSocket event listeners
        this.socket.on('detection_update', (data) => {
            this.processDetection(data);
            this.updateVisualizations();
        });

        this.socket.on('tracking_update', (data) => {
            this.updateMovementTracking(data);
        });

        this.socket.on('alert', (data) => {
            this.handleAlert(data);
        });

        // Update every second
        setInterval(() => this.calculateMetrics(), 1000);
    }

    processDetection(data) {
        const detection = {
            timestamp: new Date(),
            count: data.count,
            positions: data.positions,
            confidence: data.confidence,
            camera: data.camera
        };
        
        this.detectionHistory.push(detection);
        
        // Keep only last hour of data
        const oneHourAgo = new Date(Date.now() - 3600000);
        this.detectionHistory = this.detectionHistory.filter(d => d.timestamp > oneHourAgo);
        
        // Analyze behavior
        this.analyzeBisonBehavior(detection);
    }

    analyzeBisonBehavior(detection) {
        // Calculate movement vectors
        if (this.detectionHistory.length > 1) {
            const prevDetection = this.detectionHistory[this.detectionHistory.length - 2];
            const movements = this.calculateMovementVectors(prevDetection, detection);
            
            // Classify behaviors based on movement patterns
            const behaviors = this.classifyBehaviors(movements);
            this.updateBehaviorChart(behaviors);
        }
        
        // Update herd dynamics
        this.analyzeHerdDynamics(detection.positions);
    }

    calculateMovementVectors(prev, current) {
        const vectors = [];
        
        // Match bison between frames and calculate movement
        current.positions.forEach((pos, idx) => {
            if (prev.positions[idx]) {
                const dx = pos.x - prev.positions[idx].x;
                const dy = pos.y - prev.positions[idx].y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                const timeDiff = (current.timestamp - prev.timestamp) / 1000; // seconds
                const speed = distance / timeDiff;
                
                vectors.push({
                    speed: speed,
                    direction: Math.atan2(dy, dx) * 180 / Math.PI,
                    distance: distance,
                    bisonId: pos.id || idx
                });
            }
        });
        
        return vectors;
    }

    classifyBehaviors(movements) {
        const behaviors = {
            grazing: 0,
            moving: 0,
            resting: 0,
            alert: 0,
            unknown: 0
        };
        
        movements.forEach(movement => {
            if (movement.speed < 0.5) {
                behaviors.grazing++;
            } else if (movement.speed < 2.0) {
                behaviors.moving++;
            } else if (movement.speed < 0.1) {
                behaviors.resting++;
            } else if (movement.speed > 5.0) {
                behaviors.alert++;
            } else {
                behaviors.unknown++;
            }
        });
        
        return behaviors;
    }

    analyzeHerdDynamics(positions) {
        // Cluster analysis for herd grouping
        const clusters = this.performClustering(positions);
        
        // Update herd dynamics chart
        const bubbleData = clusters.map(cluster => ({
            x: cluster.centerX,
            y: cluster.centerY,
            r: cluster.size * 5 // Scale for visibility
        }));
        
        this.herdChart.data.datasets[0].data = bubbleData;
        this.herdChart.update('none');
    }

    performClustering(positions) {
        // Simple proximity-based clustering
        const clusters = [];
        const visited = new Set();
        const proximityThreshold = 10; // meters
        
        positions.forEach((pos, idx) => {
            if (!visited.has(idx)) {
                const cluster = {
                    positions: [pos],
                    centerX: pos.x,
                    centerY: pos.y,
                    size: 1
                };
                
                visited.add(idx);
                
                // Find nearby bison
                positions.forEach((otherPos, otherIdx) => {
                    if (!visited.has(otherIdx)) {
                        const distance = Math.sqrt(
                            Math.pow(pos.x - otherPos.x, 2) + 
                            Math.pow(pos.y - otherPos.y, 2)
                        );
                        
                        if (distance < proximityThreshold) {
                            cluster.positions.push(otherPos);
                            cluster.size++;
                            visited.add(otherIdx);
                        }
                    }
                });
                
                // Calculate cluster center
                cluster.centerX = cluster.positions.reduce((sum, p) => sum + p.x, 0) / cluster.size;
                cluster.centerY = cluster.positions.reduce((sum, p) => sum + p.y, 0) / cluster.size;
                
                clusters.push(cluster);
            }
        });
        
        return clusters;
    }

    updateBehaviorChart(behaviors) {
        const total = Object.values(behaviors).reduce((sum, val) => sum + val, 0);
        if (total > 0) {
            this.behaviorChart.data.datasets[0].data = [
                behaviors.grazing,
                behaviors.moving,
                behaviors.resting,
                behaviors.alert,
                behaviors.unknown
            ];
            this.behaviorChart.update('none');
        }
    }

    updateMovementTracking(data) {
        // Store movement data for pattern analysis
        data.tracks.forEach(track => {
            if (!this.movementPatterns.has(track.id)) {
                this.movementPatterns.set(track.id, []);
            }
            
            this.movementPatterns.get(track.id).push({
                timestamp: new Date(),
                position: track.position,
                velocity: track.velocity
            });
        });
        
        // Update movement pattern chart
        this.updateMovementChart();
        
        // Update heatmap
        this.updateHeatmap(data.tracks);
    }

    updateMovementChart() {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString();
        
        // Calculate average speed and direction changes
        let totalSpeed = 0;
        let directionChanges = 0;
        let count = 0;
        
        this.movementPatterns.forEach(pattern => {
            if (pattern.length > 1) {
                const recent = pattern[pattern.length - 1];
                const previous = pattern[pattern.length - 2];
                
                if (recent.velocity) {
                    totalSpeed += recent.velocity.magnitude || 0;
                    count++;
                }
                
                // Check for direction change
                if (recent.velocity && previous.velocity) {
                    const angleDiff = Math.abs(recent.velocity.direction - previous.velocity.direction);
                    if (angleDiff > 30) { // 30 degrees threshold
                        directionChanges++;
                    }
                }
            }
        });
        
        const avgSpeed = count > 0 ? totalSpeed / count : 0;
        
        // Update chart
        this.movementChart.data.labels.push(timeLabel);
        this.movementChart.data.datasets[0].data.push(avgSpeed);
        this.movementChart.data.datasets[1].data.push(directionChanges);
        
        // Keep only last 50 data points
        if (this.movementChart.data.labels.length > 50) {
            this.movementChart.data.labels.shift();
            this.movementChart.data.datasets[0].data.shift();
            this.movementChart.data.datasets[1].data.shift();
        }
        
        this.movementChart.update('none');
    }

    updateHeatmap(tracks) {
        if (!this.heatmapInstance) return;
        
        const heatmapData = tracks.map(track => ({
            x: Math.floor(track.position.x),
            y: Math.floor(track.position.y),
            value: track.velocity ? track.velocity.magnitude : 1
        }));
        
        this.heatmapInstance.setData({
            max: 10,
            data: heatmapData
        });
    }

    calculateMetrics() {
        // Calculate and display real-time metrics
        const metrics = {
            totalBison: this.getCurrentCount(),
            avgSpeed: this.calculateAverageSpeed(),
            herdCohesion: this.calculateHerdCohesion(),
            activityLevel: this.calculateActivityLevel(),
            alertStatus: this.determineAlertStatus()
        };
        
        this.updateMetricsDisplay(metrics);
    }

    getCurrentCount() {
        if (this.detectionHistory.length > 0) {
            return this.detectionHistory[this.detectionHistory.length - 1].count;
        }
        return 0;
    }

    calculateAverageSpeed() {
        let totalSpeed = 0;
        let count = 0;
        
        this.movementPatterns.forEach(pattern => {
            if (pattern.length > 0) {
                const recent = pattern[pattern.length - 1];
                if (recent.velocity) {
                    totalSpeed += recent.velocity.magnitude || 0;
                    count++;
                }
            }
        });
        
        return count > 0 ? (totalSpeed / count).toFixed(2) : 0;
    }

    calculateHerdCohesion() {
        // Measure how closely grouped the herd is
        if (this.detectionHistory.length === 0) return 0;
        
        const lastDetection = this.detectionHistory[this.detectionHistory.length - 1];
        if (!lastDetection.positions || lastDetection.positions.length < 2) return 100;
        
        let totalDistance = 0;
        let pairCount = 0;
        
        for (let i = 0; i < lastDetection.positions.length; i++) {
            for (let j = i + 1; j < lastDetection.positions.length; j++) {
                const dx = lastDetection.positions[i].x - lastDetection.positions[j].x;
                const dy = lastDetection.positions[i].y - lastDetection.positions[j].y;
                totalDistance += Math.sqrt(dx * dx + dy * dy);
                pairCount++;
            }
        }
        
        const avgDistance = pairCount > 0 ? totalDistance / pairCount : 0;
        // Convert to cohesion percentage (inverse of average distance)
        const cohesion = Math.max(0, Math.min(100, 100 - avgDistance * 2));
        
        return cohesion.toFixed(1);
    }

    calculateActivityLevel() {
        // Based on recent movement patterns
        const avgSpeed = this.calculateAverageSpeed();
        
        if (avgSpeed < 0.5) return 'Low';
        if (avgSpeed < 2.0) return 'Moderate';
        if (avgSpeed < 5.0) return 'High';
        return 'Very High';
    }

    determineAlertStatus() {
        // Check for unusual patterns
        const avgSpeed = parseFloat(this.calculateAverageSpeed());
        
        if (avgSpeed > this.alertThresholds.rapidMovement) {
            return { level: 'high', message: 'Rapid movement detected' };
        }
        
        const count = this.getCurrentCount();
        if (count > this.alertThresholds.crowding) {
            return { level: 'medium', message: 'High concentration of bison' };
        }
        
        return { level: 'normal', message: 'Normal activity' };
    }

    updateMetricsDisplay(metrics) {
        // Update UI elements
        document.getElementById('totalBisonCount').textContent = metrics.totalBison;
        document.getElementById('avgSpeed').textContent = `${metrics.avgSpeed} m/s`;
        document.getElementById('herdCohesion').textContent = `${metrics.herdCohesion}%`;
        document.getElementById('activityLevel').textContent = metrics.activityLevel;
        
        // Update alert status
        const alertElement = document.getElementById('alertStatus');
        if (alertElement) {
            alertElement.className = `alert-status alert-${metrics.alertStatus.level}`;
            alertElement.textContent = metrics.alertStatus.message;
        }
    }

    handleAlert(alertData) {
        // Display alert notification
        this.showNotification(alertData.message, alertData.severity);
        
        // Log alert for historical analysis
        this.logAlert(alertData);
        
        // Update alert dashboard
        this.updateAlertDashboard(alertData);
    }

    showNotification(message, severity) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast alert-${severity}`;
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">BisonGuard Alert</strong>
                <small>${new Date().toLocaleTimeString()}</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.getElementById('toastContainer').appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => toast.remove(), 5000);
    }

    logAlert(alertData) {
        const alertLog = {
            timestamp: new Date(),
            ...alertData
        };
        
        // Store in localStorage for persistence
        const alerts = JSON.parse(localStorage.getItem('bisonAlerts') || '[]');
        alerts.push(alertLog);
        
        // Keep only last 100 alerts
        if (alerts.length > 100) {
            alerts.shift();
        }
        
        localStorage.setItem('bisonAlerts', JSON.stringify(alerts));
    }

    updateAlertDashboard(alertData) {
        const alertList = document.getElementById('alertList');
        if (alertList) {
            const alertItem = document.createElement('div');
            alertItem.className = `alert-item alert-${alertData.severity}`;
            alertItem.innerHTML = `
                <span class="alert-time">${new Date().toLocaleTimeString()}</span>
                <span class="alert-message">${alertData.message}</span>
            `;
            
            alertList.insertBefore(alertItem, alertList.firstChild);
            
            // Keep only last 10 alerts visible
            while (alertList.children.length > 10) {
                alertList.removeChild(alertList.lastChild);
            }
        }
    }

    generateHourLabels() {
        const labels = [];
        for (let i = 0; i < 24; i++) {
            labels.push(`${i.toString().padStart(2, '0')}:00`);
        }
        return labels;
    }

    updateVisualizations() {
        // Called periodically to refresh all visualizations
        this.updateActivityPattern();
    }

    updateActivityPattern() {
        const now = new Date();
        const hour = now.getHours();
        
        // Update current hour's activity
        const currentActivity = this.calculateActivityLevel();
        const activityValue = currentActivity === 'Low' ? 1 : 
                            currentActivity === 'Moderate' ? 2 : 
                            currentActivity === 'High' ? 3 : 4;
        
        // Update chart
        const currentData = this.activityChart.data.datasets[0].data;
        currentData[hour] = (currentData[hour] + activityValue) / 2; // Running average
        this.activityChart.update('none');
    }

    // Export functionality
    exportAnalytics() {
        const analyticsData = {
            timestamp: new Date().toISOString(),
            detectionHistory: this.detectionHistory,
            movementPatterns: Array.from(this.movementPatterns.entries()),
            metrics: {
                totalBison: this.getCurrentCount(),
                avgSpeed: this.calculateAverageSpeed(),
                herdCohesion: this.calculateHerdCohesion(),
                activityLevel: this.calculateActivityLevel()
            }
        };
        
        const blob = new Blob([JSON.stringify(analyticsData, null, 2)], 
                             { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bisonguard_analytics_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Initialize analytics when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.bisonAnalytics = new BisonBehaviorAnalytics();
});
