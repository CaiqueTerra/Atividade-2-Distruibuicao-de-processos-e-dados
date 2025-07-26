// Smart Home API Class
class SmartHomeAPI {
    constructor() {
        this.baseURL = '';
        this.updateInterval = 5000; // 5 seconds
    }

    // Generic API call method
    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            if (data && method !== 'GET') {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(`${this.baseURL}${endpoint}`, options);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API call failed for ${endpoint}:`, error);
            throw error;
        }
    }

    // Sensor methods
    async getTemperature() {
        return this.apiCall('/api/temperatura');
    }

    async getSmoke() {
        return this.apiCall('/api/detecao-fumaca');
    }

    async getLuminosity() {
        return this.apiCall('/api/luminosidade');
    }

    // Device status methods
    async getAirConditionerStatus() {
        return this.apiCall('/api/status-ar-condicionado');
    }

    async getFireSystemStatus() {
        return this.apiCall('/api/status-sistema-incendio');
    }

    async getLightStatus() {
        return this.apiCall('/api/status-lampada');
    }

    // Device control methods
    async controlAirConditioner(action) {
        return this.apiCall(`/api/${action}-ar-condicionado`, 'POST');
    }

    async controlFireSystem(action) {
        return this.apiCall(`/api/${action}-sistema-incendio`, 'POST');
    }

    async controlLight(action) {
        return this.apiCall(`/api/${action}-lampada`, 'POST');
    }

    // Air conditioner temperature configuration
    async setAirConditionerTemperature(temperature) {
        return this.apiCall('/api/config-ar-condicionado', 'POST', { temperatura: temperature });
    }

    // Get all devices
    async getDevices() {
        return this.apiCall('/api/dispositivos');
    }
}

// Notification system
class NotificationManager {
    constructor() {
        this.container = this.createContainer();
    }

    createContainer() {
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(container);
        }
        return container;
    }

    show(message, type = 'success', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            padding: 1rem 1.5rem;
            border-radius: 10px;
            color: white;
            font-weight: 500;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transform: translateX(400px);
            transition: transform 0.3s ease;
            background: ${type === 'success' ? '#48bb78' : type === 'error' ? '#f56565' : '#4299e1'};
        `;

        this.container.appendChild(notification);

        // Trigger animation
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove notification
        setTimeout(() => {
            notification.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, duration);
    }
}

// Chart utilities
class ChartManager {
    constructor() {
        this.charts = {};
        this.maxDataPoints = 20;
    }

    createLineChart(canvasId, color) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: color,
                    backgroundColor: color + '20',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: { display: false }
                }
            }
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    addDataPoint(chartId, value) {
        const chart = this.charts[chartId];
        if (!chart) return;

        const now = new Date().toLocaleTimeString();
        
        if (chart.data.labels.length >= this.maxDataPoints) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(value);
        chart.update('none');
    }

    destroyChart(chartId) {
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
        }
    }
}


const utils = {
    formatTemperature: (temp) => temp ? `${temp.toFixed(1)}°C` : '--',
    formatTime: (date) => date ? date.toLocaleTimeString() : '--',
    formatUptime: (startTime) => {
        if (!startTime) return '0m';
        const now = new Date();
        const diff = now - startTime;
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
    },
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};


const api = new SmartHomeAPI();
const notifications = new NotificationManager();
const charts = new ChartManager();


if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SmartHomeAPI, NotificationManager, ChartManager, utils };
}
