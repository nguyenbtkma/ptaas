// ========================================
// Common Utilities & Helpers
// ========================================

/**
 * Format date to readable format
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format duration in seconds to readable string
 */
function formatDuration(seconds) {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    let result = [];
    if (hours > 0) result.push(`${hours}h`);
    if (minutes > 0) result.push(`${minutes}m`);
    if (secs > 0 || result.length === 0) result.push(`${secs}s`);

    return result.join(' ');
}

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
    const statusMap = {
        'SUCCESS': { class: 'status-badge success', text: '✓ Success' },
        'FAILURE': { class: 'status-badge failure', text: '✗ Failed' },
        'PENDING': { class: 'status-badge pending', text: '⧗ Pending' },
        'RUNNING': { class: 'status-badge running', text: '⟳ Running' },
        'QUEUED': { class: 'status-badge pending', text: '⧗ Queued' },
        'COMPLETED': { class: 'status-badge success', text: '✓ Completed' },
        'success': { class: 'status-badge success', text: '✓ Success' },
        'failed': { class: 'status-badge failure', text: '✗ Failed' },
        'running': { class: 'status-badge running', text: '⟳ Running' },
        'queued': { class: 'status-badge pending', text: '⧗ Queued' },
        'completed': { class: 'status-badge success', text: '✓ Completed' }
    };

    const info = statusMap[status] || { class: 'status-badge', text: status };
    return `<span class="${info.class}">${info.text}</span>`;
}

/**
 * Get severity badge HTML
 */
function getSeverityBadge(severity) {
    if (!severity) return '<span class="severity-info">Info</span>';
    
    const sevMap = {
        'Critical': 'severity-critical',
        'High': 'severity-high',
        'Medium': 'severity-medium',
        'Low': 'severity-low',
        'Info': 'severity-info'
    };

    const className = sevMap[severity] || 'severity-info';
    return `<span class="${className}">${severity}</span>`;
}

/**
 * Show notification/toast
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: ${type === 'error' ? '#e74c3c' : type === 'success' ? '#27ae60' : '#3498db'};
        color: white;
        padding: 15px 20px;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, duration);
}

/**
 * Clear table body
 */
function clearTable(tableId) {
    const tbody = document.getElementById(tableId);
    if (tbody) {
        tbody.innerHTML = '';
    }
}

/**
 * Add loading state to table
 */
function setTableLoading(tableId, message = 'Loading...') {
    const tbody = document.getElementById(tableId);
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="10" class="loading">${message}</td></tr>`;
    }
}

/**
 * Close scan status panel
 */
function closeScanStatus() {
    const panel = document.getElementById('scanStatusPanel');
    if (panel) {
        panel.style.display = 'none';
    }
}

/**
 * Go to history page
 */
function goToHistory() {
    showPage('history');
    loadHistoryList();
}

/**
 * Update scan options based on selected type
 */
function updateScanOptions() {
    const scanType = document.getElementById('scanType').value;
    
    // Hide all options
    const optionEls = document.querySelectorAll('.scan-options');
    optionEls.forEach(el => {
        if (el) el.style.display = 'none';
    });

    // Show selected type options
    if (scanType === 'nmap') {
        const el = document.getElementById('nmapOptions');
        if (el) el.style.display = 'block';
        const hint = document.getElementById('targetHint');
        if (hint) hint.textContent = 'e.g., scanme.nmap.org or 192.168.1.1';
    } else if (scanType === 'zap') {
        const el = document.getElementById('zapOptions');
        if (el) el.style.display = 'block';
        const hint = document.getElementById('targetHint');
        if (hint) hint.textContent = 'e.g., http://testphp.vulnweb.com';
    } else if (scanType === 'sqlmap') {
        const el = document.getElementById('sqlmapOptions');
        if (el) el.style.display = 'block';
        const hint = document.getElementById('targetHint');
        if (hint) hint.textContent = 'e.g., http://testphp.vulnweb.com?id=1';
    }
}

/**
 * Collect scan options from form
 */
function collectScanOptions() {
    const scanType = document.getElementById('scanType').value;
    let options = '';

    if (scanType === 'nmap') {
        const checks = document.querySelectorAll('#nmapOptions input[type="checkbox"]:checked');
        options = Array.from(checks).map(c => c.value).join(' ');
    } else if (scanType === 'zap') {
        const mode = document.getElementById('zapMode').value;
        options = mode;
    } else if (scanType === 'sqlmap') {
        const checks = document.querySelectorAll('#sqlmapOptions input[type="checkbox"]:checked');
        options = Array.from(checks).map(c => c.value).join(' ');
    }

    const custom = document.getElementById('customOptions').value.trim();
    if (custom) {
        options = options ? `${options} ${custom}` : custom;
    }

    return options;
}

/**
 * Poll scan status with interval
 */
async function pollScanStatus(taskId, onUpdate, onComplete, interval = 2000) {
    const maxAttempts = 3600 * 1000 / interval; // 1 hour max
    let attempts = 0;

    const poll = async () => {
        try {
            const status = await getScanStatus(taskId);
            
            if (onUpdate) {
                onUpdate(status);
            }

            if (status.state === 'SUCCESS' || status.state === 'FAILURE') {
                if (onComplete) {
                    onComplete(status);
                }
                return;
            }

            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, interval);
            }
        } catch (error) {
            console.error('Error polling status:', error);
            setTimeout(poll, interval);
        }
    };

    poll();
}

/**
 * Get scan type icon
 */
function getScanTypeIcon(scanType) {
    const icons = {
        'nmap': '🌐',
        'zap': '🔍',
        'sqlmap': '💾'
    };
    return icons[scanType] || '📊';
}

/**
 * Get scan type label
 */
function getScanTypeLabel(scanType) {
    const labels = {
        'nmap': 'Network Scan',
        'zap': 'Web App Scan',
        'sqlmap': 'SQL Injection'
    };
    return labels[scanType] || scanType;
}

/**
 * Show schedule form
 */
function showScheduleForm() {
    document.getElementById('scheduleFormContainer').style.display = 'block';
    document.getElementById('scheduleForm').reset();
}

/**
 * Hide schedule form
 */
function hideScheduleForm() {
    document.getElementById('scheduleFormContainer').style.display = 'none';
}

/**
 * Format finding description
 */
function formatFindingDescription(description) {
    if (!description) return 'N/A';
    return description.substring(0, 100) + (description.length > 100 ? '...' : '');
}

/**
 * Build finding detail HTML
 */
function buildFindingDetail(finding) {
    return `
        <div class="finding-detail">
            <div class="detail-section">
                <h4>Title</h4>
                <p>${finding.title || 'N/A'}</p>
            </div>
            <div class="detail-section">
                <h4>Severity</h4>
                ${getSeverityBadge(finding.severity)}
            </div>
            <div class="detail-section">
                <h4>Description</h4>
                <p>${finding.description || 'N/A'}</p>
            </div>
            <div class="detail-section">
                <h4>Mitigation</h4>
                <p>${finding.mitigation || 'N/A'}</p>
            </div>
            <div class="detail-section">
                <h4>Impact</h4>
                <p>${finding.impact || 'N/A'}</p>
            </div>
            ${finding.cve ? `<div class="detail-section"><h4>CVE</h4><p>${finding.cve}</p></div>` : ''}
            <div class="detail-section">
                <h4>Date</h4>
                <p>${formatDate(finding.date)}</p>
            </div>
        </div>
    `;
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    .notification {
        animation: slideIn 0.3s ease !important;
    }

    .finding-detail {
        font-size: 14px;
    }

    .detail-section {
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 1px solid #ecf0f1;
    }

    .detail-section:last-child {
        border-bottom: none;
    }

    .detail-section h4 {
        color: #2c3e50;
        margin-bottom: 8px;
        font-weight: 600;
    }

    .detail-section p {
        color: #555;
        line-height: 1.5;
        word-break: break-word;
    }

    .detail-section code {
        background-color: #f8f9fa;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
    }
`;
document.head.appendChild(style);
