// ========================================
// Scan Module
// ========================================

/**
 * Handle scan form submission
 */
async function handleScanSubmit(e) {
    e.preventDefault();

    const scanType = document.getElementById('scanType').value;
    const target = document.getElementById('target').value.trim();
    const options = collectScanOptions();

    if (!scanType || !target) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }

    try {
        // Disable submit button
        const submitBtn = document.querySelector('#scanForm button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Starting...';

        // Start scan
        const response = await startScan(scanType, target, options);
        const taskId = response.task_id;

        // Do not show single-task panel; rely on Active Jobs list
        showNotification(`Scan started! Task ID: ${taskId}`, 'success');

        // Kick Active Jobs refresh to show the new job
        try { startActiveJobsAutoRefresh(); refreshActiveJobs(); } catch (err) {}

        // Optionally poll for completion to show final notification only
        pollScanStatus(taskId, null, onScanComplete);

        // Reset form
        document.getElementById('scanForm').reset();
        updateScanOptions();

        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 Start Scan';

    } catch (error) {
        console.error('Error starting scan:', error);
        showNotification('Error starting scan: ' + error.message, 'error');

        const submitBtn = document.querySelector('#scanForm button[type="submit"]');
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 Start Scan';
    }
}

/**
 * Update progress while scan is running
 */
function updateScanProgress(status) {
    // This function is no longer used for UI updates; left for optional future use
    const stateDisplay = {
        'PENDING': 'Waiting...',
        'RUNNING': 'Scanning...',
        'SUCCESS': 'Complete',
        'FAILURE': 'Failed',
        'RETRY': 'Retrying...'
    };

    const stateValue = status.state || status.status;
    // No-op UI updates
}

/**
 * Called when scan completes
 */
function onScanComplete(status) {
    const isSuccess = status.state === 'SUCCESS' || status.state === 'success';

    if (isSuccess) {
        showNotification('Scan completed successfully!', 'success', 5000);
    } else {
        showNotification('Scan failed. Check details for more info.', 'error', 5000);
    }

    // Refresh Active Jobs list to reflect completion
    try { refreshActiveJobs(); } catch (err) {}
}

// ========================================
// Active Jobs (Scan page only)
// ========================================
let activeJobsInterval = null;

function startActiveJobsAutoRefresh() {
    if (activeJobsInterval) {
        clearInterval(activeJobsInterval);
    }
    refreshActiveJobs();
    activeJobsInterval = setInterval(refreshActiveJobs, 2000);
}

function stopActiveJobsAutoRefresh() {
    if (activeJobsInterval) {
        clearInterval(activeJobsInterval);
        activeJobsInterval = null;
    }
}

async function refreshActiveJobs() {
    try {
        const tbody = document.getElementById('activeJobsBody');
        if (!tbody) return;
        const active = await getActiveScans();
        if (!active || active.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No active jobs</td></tr>';
            return;
        }
        tbody.innerHTML = '';
        active.forEach(job => {
            const statusBadge = getStatusBadge((job.status || job.state || 'Queued').toUpperCase());
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${getScanTypeIcon(job.scan_type)} ${getScanTypeLabel(job.scan_type)}</td>
                <td style="word-break: break-all;">${job.target || '-'}</td>
                <td>${statusBadge}</td>
                <td>${Math.round(job.progress || 0)}%</td>
                <td>${formatDate(job.created || new Date().toISOString())}</td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error('Error refreshing active jobs:', err);
    }
}
