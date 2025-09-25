// Chart.js initialization and management for BisonGuard Analytics

// Initialize all charts
function initializeCharts() {
    // Wait for DOM to be ready
    setTimeout(() => {
        initTimelineChart();
        initDistributionChart();
        initConfidenceChart();
        initMovementChart();
    }, 500);
}

// Initialize timeline chart
function initTimelineChart() {
    const ctx = document.getElementById('timeline-chart');
    if (!ctx) return;
    
    charts.timeline = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Detections',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: false 
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: { 
                    beginAtZero: true,
                    grid: { 
                        color: 'rgba(255, 255, 255, 0.1)' 
                    },
                    ticks: { 
                        color: 'rgba(255, 255, 255, 0.8)' 
                    }
                },
                x: {
                    grid: { 
                        color: 'rgba(255, 255, 255, 0.1)' 
                    },
                    ticks: { 
                        color: 'rgba(255, 255, 255, 0.8)',
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// Initialize distribution chart
function initDistributionChart() {
    const ctx = document.getElementById('distribution-chart');
    if (!ctx) return;
    
    charts.distribution = new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Camera 1', 'Camera 2'],
            datasets: [{
                data: [0, 0],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(239, 68, 68, 0.8)'
                ],
                borderColor: 'rgba(255, 255, 255, 0.2)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { 
                        color: 'rgba(255, 255, 255, 0.8)',
                        padding: 15
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Initialize confidence distribution chart
function initConfidenceChart() {
    const ctx = document.getElementById('confidence-chart');
    if (!ctx) return;
    
    charts.confidence = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['0.3-0.4', '0.4-0.5', '0.5-0.6', '0.6-0.7', '0.7-0.8', '0.8-0.9', '0.9-1.0'],
            datasets: [{
                label: 'Detection Count',
                data: [0, 0, 0, 0, 0, 0, 0],
                backgroundColor: 'rgba(16, 185, 129, 0.8)',
                borderColor: 'rgba(16, 185, 129, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: false 
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { 
                        color: 'rgba(255, 255, 255, 0.1)' 
                    },
                    ticks: { 
                        color: 'rgba(255, 255, 255, 0.8)',
                        stepSize: 1
                    }
                },
                x: {
                    grid: { 
                        color: 'rgba(255, 255, 255, 0.1)' 
                    },
                    ticks: { 
                        color: 'rgba(255, 255, 255, 0.8)' 
                    }
                }
            }
        }
    });
}

// Initialize movement pattern chart
function initMovementChart() {
    const ctx = document.getElementById('movement-chart');
    if (!ctx) return;
    
    charts.movement = new Chart(ctx.getContext('2d'), {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Movement Speed',
                data: [],
                backgroundColor: 'rgba(245, 158, 11, 0.8)',
                borderColor: 'rgba(245, 158, 11, 1)',
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: false 
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Speed: ${context.parsed.y.toFixed(1)} px/s at ${context.parsed.x}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    title: { 
                        display: true, 
                        text: 'Speed (px/s)', 
                        color: 'rgba(255, 255, 255, 0.8)' 
                    },
                    grid: { 
                        color: 'rgba(255, 255, 255, 0.1)' 
                    },
                    ticks: { 
                        color: 'rgba(255, 255, 255, 0.8)' 
                    }
                },
                x: {
                    type: 'linear',
                    title: { 
                        display: true, 
                        text: 'Time (seconds)', 
                        color: 'rgba(255, 255, 255, 0.8)' 
                    },
                    grid: { 
                        color: 'rgba(255, 255, 255, 0.1)' 
                    },
                    ticks: { 
                        color: 'rgba(255, 255, 255, 0.8)' 
                    }
                }
            }
        }
    });
}

// Update charts with new data
function updateCharts(data) {
    updateTimelineChart(data);
    updateDistributionChart(data);
    
    if (data.movement) {
        updateMovementChart(data.movement);
    }
}

// Update timeline chart
function updateTimelineChart(data) {
    if (!charts.timeline) return;
    
    const now = new Date();
    const label = now.toLocaleTimeString();
    
    // Add new data point
    if (charts.timeline.data.labels.length > 30) {
        charts.timeline.data.labels.shift();
        charts.timeline.data.datasets[0].data.shift();
    }
    
    charts.timeline.data.labels.push(label);
    charts.timeline.data.datasets[0].data.push(data.current_count || 0);
    charts.timeline.update('none'); // No animation for smoother updates
}

// Update distribution chart
function updateDistributionChart(data) {
    if (!charts.distribution) return;
    
    // This would be updated based on camera-specific data
    // For now, using placeholder logic
    if (data.current_count) {
        const cam1Count = Math.floor(data.current_count * 0.6);
        const cam2Count = data.current_count - cam1Count;
        
        charts.distribution.data.datasets[0].data = [cam1Count, cam2Count];
        charts.distribution.update();
    }
}

// Update movement chart
function updateMovementChart(movementData) {
    if (!charts.movement) return;
    
    if (movementData.avg_speed !== undefined) {
        const now = Date.now() / 1000; // Convert to seconds
        
        // Add new data point
        charts.movement.data.datasets[0].data.push({
            x: now,
            y: movementData.avg_speed
        });
        
        // Keep only last 50 points
        if (charts.movement.data.datasets[0].data.length > 50) {
            charts.movement.data.datasets[0].data.shift();
        }
        
        charts.movement.update('none');
    }
}

// Update confidence distribution
function updateConfidenceChart(confidenceData) {
    if (!charts.confidence || !confidenceData) return;
    
    // Process confidence data into bins
    const bins = [0, 0, 0, 0, 0, 0, 0];
    confidenceData.forEach(conf => {
        if (conf >= 0.3 && conf < 0.4) bins[0]++;
        else if (conf >= 0.4 && conf < 0.5) bins[1]++;
        else if (conf >= 0.5 && conf < 0.6) bins[2]++;
        else if (conf >= 0.6 && conf < 0.7) bins[3]++;
        else if (conf >= 0.7 && conf < 0.8) bins[4]++;
        else if (conf >= 0.8 && conf < 0.9) bins[5]++;
        else if (conf >= 0.9) bins[6]++;
    });
    
    charts.confidence.data.datasets[0].data = bins;
    charts.confidence.update();
}

// Update historical charts with fetched data
function updateHistoricalCharts(data) {
    if (!data.hourly || data.hourly.length === 0) return;
    
    // Update timeline with historical data
    if (charts.timeline) {
        const labels = data.hourly.map(h => {
            const date = new Date(h.hour);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });
        const counts = data.hourly.map(h => h.count);
        
        charts.timeline.data.labels = labels;
        charts.timeline.data.datasets[0].data = counts;
        charts.timeline.update();
    }
    
    // Update confidence distribution if available
    if (data.hourly && charts.confidence) {
        const allConfidences = data.hourly
            .filter(h => h.confidence)
            .map(h => h.confidence);
        
        if (allConfidences.length > 0) {
            updateConfidenceChart(allConfidences);
        }
    }
}

// Destroy all charts (for cleanup)
function destroyCharts() {
    Object.values(charts).forEach(chart => {
        if (chart) chart.destroy();
    });
    charts = {};
}

// Export functions to global scope
window.initializeCharts = initializeCharts;
window.updateCharts = updateCharts;
window.updateHistoricalCharts = updateHistoricalCharts;
window.destroyCharts = destroyCharts;
