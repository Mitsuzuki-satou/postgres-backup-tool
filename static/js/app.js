// Main application JavaScript
console.log('PostgreSQL Backup & Restore Tool - Web Interface Loaded');

// Auto-refresh functionality
let autoRefreshInterval;

function startAutoRefresh() {
    autoRefreshInterval = setInterval(() => {
        loadDashboardData();
        const activeTab = document.querySelector('.tab-button.active');
        if (activeTab) {
            const tabName = activeTab.dataset.tab;
            if (tabName === 'backups') loadBackups();
            else if (tabName === 'logs') loadLogs();
        }
    }, 30000); // Refresh every 30 seconds
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
}

// Start auto-refresh when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeEnhancedComponents();
    startAutoRefresh();
});

function initializeEnhancedComponents() {
    // Initialize Select2 components if available
    if (typeof $ !== 'undefined' && $.fn.select2) {
        $('.backup-select, .credential-select').select2({
            theme: 'bootstrap4',
            width: '100%'
        });
    }
    
    // Initialize Flatpickr for date/time selection
    if (typeof flatpickr !== 'undefined') {
        flatpickr(".datetime-picker", {
            enableTime: true,
            dateFormat: "Y-m-d H:i",
            theme: "dark"
        });
    }
    
    // Configure toastr if available
    if (typeof toastr !== 'undefined') {
        toastr.options = {
            "closeButton": true,
            "debug": false,
            "newestOnTop": false,
            "progressBar": true,
            "positionClass": "toast-top-right",
            "preventDuplicates": false,
            "onclick": null,
            "showDuration": "300",
            "hideDuration": "1000",
            "timeOut": "5000",
            "extendedTimeOut": "1000",
            "showEasing": "swing",
            "hideEasing": "linear",
            "showMethod": "fadeIn",
            "hideMethod": "fadeOut"
        };
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});

// Utility functions
function showNotification(message, type = 'info') {
    // Use toastr for notifications if available
    if (typeof toastr !== 'undefined') {
        switch(type) {
            case 'success':
                toastr.success(message);
                break;
            case 'error':
                toastr.error(message);
                break;
            case 'warning':
                toastr.warning(message);
                break;
            default:
                toastr.info(message);
        }
    } else {
        // Fallback to basic notification
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            type === 'warning' ? 'bg-yellow-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// API helper functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showNotification('API call failed: ' + error.message, 'error');
        throw error;
    }
}

// Dashboard functions
async function loadDashboardData() {
    try {
        const status = await apiCall('/api/status');
        updateSystemStatus(status);
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

function updateSystemStatus(status) {
    const statusElement = document.getElementById('system-status');
    if (statusElement) {
        statusElement.textContent = status.status;
        statusElement.className = status.status === 'running' ? 'text-green-600' : 'text-red-600';
    }
    
    const activeBackupsElement = document.getElementById('active-backups');
    if (activeBackupsElement) {
        activeBackupsElement.textContent = status.active_backups;
    }
    
    const activeRestoresElement = document.getElementById('active-restores');
    if (activeRestoresElement) {
        activeRestoresElement.textContent = status.active_restores;
    }
}

async function loadBackups() {
    try {
        const data = await apiCall('/api/backups');
        displayBackups(data.backups);
    } catch (error) {
        console.error('Failed to load backups:', error);
    }
}

function displayBackups(backups) {
    const container = document.getElementById('backups-list');
    if (!container) return;
    
    if (backups.length === 0) {
        container.innerHTML = '<p class="text-gray-500">No backups found</p>';
        return;
    }
    
    container.innerHTML = backups.map(backup => `
        <div class="border rounded p-3 mb-2">
            <div class="flex justify-between items-center">
                <div>
                    <h4 class="font-medium">${backup.name}</h4>
                    <p class="text-sm text-gray-600">Size: ${formatFileSize(backup.size)}</p>
                    <p class="text-sm text-gray-600">Created: ${new Date(backup.created * 1000).toLocaleString()}</p>
                </div>
                <div class="space-x-2">
                    <button onclick="restoreBackup('${backup.path}')" class="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600">
                        Restore
                    </button>
                    <button onclick="deleteBackup('${backup.path}')" class="bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600">
                        Delete
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

async function loadLogs() {
    try {
        const data = await apiCall('/api/logs');
        displayLogs(data.logs);
    } catch (error) {
        console.error('Failed to load logs:', error);
    }
}

function displayLogs(logs) {
    const container = document.getElementById('logs-container');
    if (!container) return;
    
    if (logs.length === 0) {
        container.innerHTML = '<p class="text-gray-500">No logs available</p>';
        return;
    }
    
    container.innerHTML = logs.map(log => `
        <div class="border-b pb-2 mb-2">
            <div class="flex justify-between items-start">
                <span class="text-sm font-medium ${getLogLevelClass(log.level)}">${log.level}</span>
                <span class="text-xs text-gray-500">${new Date(log.timestamp).toLocaleString()}</span>
            </div>
            <p class="text-sm mt-1">${log.message}</p>
        </div>
    `).join('');
}

function getLogLevelClass(level) {
    switch (level.toUpperCase()) {
        case 'ERROR': return 'text-red-600';
        case 'WARNING': return 'text-yellow-600';
        case 'INFO': return 'text-blue-600';
        default: return 'text-gray-600';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function loadConfig() {
    try {
        const data = await apiCall('/api/config');
        populateConfigForm(data);
    } catch (error) {
        console.error('Failed to load configuration:', error);
    }
}

function populateConfigForm(config) {
    // Populate source database config
    const sourceConfig = config.database?.source || {};
    document.getElementById('source-host').value = sourceConfig.host || '';
    document.getElementById('source-port').value = sourceConfig.port || 5432;
    document.getElementById('source-database').value = sourceConfig.database || '';
    document.getElementById('source-username').value = sourceConfig.username || '';
    document.getElementById('source-password').value = sourceConfig.password || '';
    document.getElementById('source-ssl-mode').value = sourceConfig.ssl_mode || 'prefer';
    
    // Populate target database config
    const targetConfig = config.database?.target || {};
    document.getElementById('target-host').value = targetConfig.host || '';
    document.getElementById('target-port').value = targetConfig.port || 5432;
    document.getElementById('target-database').value = targetConfig.database || '';
    document.getElementById('target-username').value = targetConfig.username || '';
    document.getElementById('target-password').value = targetConfig.password || '';
    document.getElementById('target-ssl-mode').value = targetConfig.ssl_mode || 'prefer';
}

async function testConnection(type) {
    try {
        const config = type === 'source' ? getSourceConfig() : getTargetConfig();
        const response = await apiCall('/api/test-connection', {
            method: 'POST',
            body: JSON.stringify({
                type: "database",
                config: config
            })
        });
        
        if (response.status === 'success') {
            showNotification(`${type} database connection successful`, 'success');
        } else {
            showNotification(`${type} database connection failed: ${response.message}`, 'error');
        }
    } catch (error) {
        showNotification(`Connection test failed: ${error.message}`, 'error');
    }
}

function getSourceConfig() {
    return {
        host: document.getElementById('source-host').value,
        port: parseInt(document.getElementById('source-port').value),
        database: document.getElementById('source-database').value,
        username: document.getElementById('source-username').value,
        password: document.getElementById('source-password').value,
        ssl_mode: document.getElementById('source-ssl-mode').value
    };
}

function getTargetConfig() {
    return {
        host: document.getElementById('target-host').value,
        port: parseInt(document.getElementById('target-port').value),
        database: document.getElementById('target-database').value,
        username: document.getElementById('target-username').value,
        password: document.getElementById('target-password').value,
        ssl_mode: document.getElementById('target-ssl-mode').value
    };
}

async function saveConfig() {
    try {
        const config = {
            database: {
                source: getSourceConfig(),
                target: getTargetConfig()
            }
        };
        
        await apiCall('/api/config', {
            method: 'PUT',
            body: JSON.stringify(config)
        });
        
        showNotification('Configuration saved successfully', 'success');
    } catch (error) {
        showNotification('Failed to save configuration: ' + error.message, 'error');
    }
}

async function createBackup() {
    try {
        const sourceConfig = getSourceConfig();
        const backupConfig = {
            backup_type: document.getElementById('backup-type')?.value || 'full',
            compression: document.getElementById('compression')?.value || 'gzip',
            parallel_jobs: parseInt(document.getElementById('parallel-jobs')?.value || 4)
        };
        
        const job = {
            name: `Backup ${new Date().toISOString()}`,
            source_config: sourceConfig,
            backup_config: backupConfig
        };
        
        const response = await apiCall('/api/backup', {
            method: 'POST',
            body: JSON.stringify(job)
        });
        
        showNotification('Backup started: ' + response.job_id, 'success');
    } catch (error) {
        showNotification('Failed to start backup: ' + error.message, 'error');
    }
}

async function restoreBackup(backupPath) {
    try {
        const targetConfig = getTargetConfig();
        
        const response = await apiCall('/api/restore', {
            method: 'POST',
            body: JSON.stringify({
                backup_file: backupPath,
                target_config: targetConfig
            })
        });
        
        showNotification('Restore started', 'success');
    } catch (error) {
        showNotification('Failed to start restore: ' + error.message, 'error');
    }
}

async function deleteBackup(backupPath) {
    if (!confirm('Are you sure you want to delete this backup?')) {
        return;
    }
    
    try {
        // This would need a delete endpoint implementation
        showNotification('Delete functionality not yet implemented', 'warning');
    } catch (error) {
        showNotification('Failed to delete backup: ' + error.message, 'error');
    }
}

// Tab switching functionality
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active', 'bg-blue-600', 'text-white');
        button.classList.add('bg-gray-200', 'text-gray-700');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(tabName + '-tab');
    if (selectedContent) {
        selectedContent.classList.remove('hidden');
    }
    
    // Add active class to selected tab button
    const selectedButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (selectedButton) {
        selectedButton.classList.add('active', 'bg-blue-600', 'text-white');
        selectedButton.classList.remove('bg-gray-200', 'text-gray-700');
    }
    
    // Load tab-specific data
    if (tabName === 'backups') {
        loadBackups();
    } else if (tabName === 'logs') {
        loadLogs();
    } else if (tabName === 'config') {
        loadConfig();
    }
}

// Export for use in templates
window.appUtils = {
    showNotification,
    apiCall,
    startAutoRefresh,
    stopAutoRefresh,
    loadDashboardData,
    loadBackups,
    loadLogs,
    loadConfig,
    testConnection,
    saveConfig,
    createBackup,
    restoreBackup,
    deleteBackup,
    switchTab
};