// ========================================
// History Module
// ========================================

let allScans = [];
let historyRefreshInterval = null;
const HISTORY_REFRESH_INTERVAL = 5000; // Poll every 5 seconds to reduce flicker
let historyInitialLoad = true;

/**
 * Start auto-refresh of history to track scan status in real-time
 */
function startHistoryAutoRefresh() {
    if (historyRefreshInterval) {
        clearInterval(historyRefreshInterval);
    }
    
    // Initial load
    historyInitialLoad = true;
    loadHistoryList(false); // show loading only on initial load
    
    // Set up polling
    historyRefreshInterval = setInterval(() => {
        loadHistoryList(true); // silent refresh, no loading flicker
    }, HISTORY_REFRESH_INTERVAL);
}

/**
 * Stop auto-refresh of history
 */
function stopHistoryAutoRefresh() {
    if (historyRefreshInterval) {
        clearInterval(historyRefreshInterval);
        historyRefreshInterval = null;
    }
}

/**
 * Load and display scan history
 */
async function loadHistoryList(silent = false) {
    try {
        if (!silent) {
            setTableLoading('historyBody', 'Loading scan history...');
        }

        // Fetch findings, tests, engagements in parallel (completed scans only)
        const [dataFindings, dataTests, dataEngagements] = await Promise.all([
            fetch(`${BACKEND_URL}/dojo/findings?limit=10000`).then(r => r.json()),
            fetch(`${BACKEND_URL}/dojo/tests?limit=1000`).then(r => r.json()),
            fetch(`${BACKEND_URL}/dojo/engagements?limit=1000`).then(r => r.json())
        ]);
        
        const findings = Array.isArray(dataFindings) ? dataFindings : (dataFindings.results || dataFindings.value || []);
        const testsRaw = Array.isArray(dataTests) ? dataTests : (dataTests.results || dataTests.value || []);
        const tests = testsRaw.filter(t => {
            const statusText = (t.status || '').toLowerCase();
            const pct = Number(t.percent_complete || 0);
            // Only keep completed/failed tests; drop running
            return statusText === 'completed' || statusText === 'failed' || pct >= 100;
        });
        const engagements = Array.isArray(dataEngagements) ? dataEngagements : (dataEngagements.results || dataEngagements.value || []);
        
        // Build engagement map for quick lookup
        const engagementMap = {};
        engagements.forEach(eng => {
            engagementMap[eng.id] = eng;
        });
        
        // Helper: Normalize scan type string to one of nmap/zap/sqlmap
        function normalizeType(scanType, testTypeName, engagementName) {
            const t = (scanType || testTypeName || '').toLowerCase();
            if (t.includes('nmap')) return 'nmap';
            if (t.includes('zap')) return 'zap';
            if (t.includes('sqlmap')) return 'sqlmap';
            // Generic Findings Import created by SQLMap
            if (t.includes('generic') && (engagementName || '').toLowerCase().includes('sqlmap')) return 'sqlmap';
            return (scanType || testTypeName || 'unknown').toLowerCase();
        }

        // Build test map for quick lookup
        const testMap = {};
        tests.forEach(test => {
            testMap[test.id] = test;
        });
        
        // Initialize scans from tests (so tests with zero findings still show)
        const scanMap = {};
        tests.forEach(testInfo => {
            const engagement = engagementMap[testInfo.engagement] || {};
            let target = 'Unknown';
            if (engagement.name) {
                const parts = engagement.name.split(' - ');
                target = parts.length > 1 ? parts.slice(1).join(' - ') : engagement.name;
            }
            const typeNorm = normalizeType(testInfo.scan_type, testInfo.test_type_name, engagement.name);
            scanMap[testInfo.id] = {
                id: testInfo.id,
                test: {
                    id: testInfo.id,
                    target: target,
                    scan_type: typeNorm,
                    created_on: testInfo.created || testInfo.target_start,
                    start_date: testInfo.target_start,
                    end_date: testInfo.target_end || testInfo.end_date,
                    estimated_time: testInfo.estimated_time || 0,
                    engagement_name: engagement.name || '',
                    status: 'Completed',
                    progress: 100,
                    percent_complete: testInfo.percent_complete || 100
                },
                findings: [],
                severity: null
            };
        });

        // Group findings by test ID and merge into scanMap
        findings.forEach(finding => {
            const testId = finding.test;
            if (!testId) return;
            // Only attach findings for completed tests we kept
            if (!scanMap[testId]) return;

            scanMap[testId].findings.push(finding);
            scanMap[testId].severity = getSeverity(scanMap[testId].findings);
        });

        // Only completed DefectDojo scans (no active task log merge)
        allScans = Object.values(scanMap);

        // Sort by created_on DESC (newest first)
        allScans.sort((a, b) => {
            const dateA = new Date(a.test.created_on || a.test.start_date || 0);
            const dateB = new Date(b.test.created_on || b.test.start_date || 0);
            return dateB - dateA; // newest first
        });

        // Initial render vs incremental update to avoid flicker
        if (historyInitialLoad || !silent) {
            displayHistoryTable(allScans);
            historyInitialLoad = false;
        } else {
            updateHistoryTable(allScans);
        }

    } catch (error) {
        console.error('Error loading history:', error);
        showNotification('Error loading history', 'error');
        if (!silent) {
            document.getElementById('historyBody').innerHTML = '<tr><td colspan="7">Error loading history</td></tr>';
        }
    }
}

/**
 * Display scans in history table
 */
function displayHistoryTable(scans) {
    const tbody = document.getElementById('historyBody');
    tbody.innerHTML = '';

    if (scans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No scan history yet</td></tr>';
        return;
    }

    scans.forEach(scan => {
        const row = document.createElement('tr');
        row.setAttribute('data-id', String(scan.id));
        row.innerHTML = buildHistoryRowHtml(scan);
        tbody.appendChild(row);
    });
}

function buildHistoryRowHtml(scan) {
    const test = scan.test || {};
    const scanType = test.scan_type || 'unknown';
    const target = test.target || test.engagement_name || 'Unknown';
    const findings = scan.findings || [];
    const percentComplete = Number(test.percent_complete || 100);
    const statusRaw = (test.status || '').toLowerCase();
    const status = statusRaw === 'failed' ? 'Failed' : (percentComplete >= 100 ? 'Success' : 'Failed');
    const progress = 100;
    let statusDisplay = getStatusBadge(status.toUpperCase());
    if (progress > 0 && progress < 100) {
        statusDisplay += ` <span style="color:#7f8c8d; font-size:12px;">${progress}%</span>`;
    }
    let durationDisplay = 'N/A';
    const start = test.start_date || test.created_on;
    const end = test.end_date;
    if (start && end) {
        const diffSecs = Math.max(0, (new Date(end) - new Date(start)) / 1000);
        if (diffSecs < 1) {
            durationDisplay = Math.round(diffSecs * 1000) + 'ms';
        } else {
            durationDisplay = diffSecs.toFixed(1) + 's';
        }
    } else if (test.estimated_time && test.estimated_time > 0) {
        if (test.estimated_time < 1) {
            durationDisplay = Math.round(test.estimated_time * 1000) + 'ms';
        } else {
            durationDisplay = test.estimated_time.toFixed(1) + 's';
        }
    }
    const createdTime = test.start_date || test.created_on;
    const createdDisplay = createdTime ? formatDate(createdTime) : 'N/A';
    const typeShort = scanType === 'nmap' ? 'Nmap' : (scanType === 'zap' ? 'ZAP' : (scanType === 'sqlmap' ? 'SQLMap' : scanType));
    return `
        <td>${getScanTypeIcon(scanType)} ${typeShort}</td>
        <td style="word-break: break-all;">${target}</td>
        <td>${statusDisplay}</td>
        <td><strong>${findings.length}</strong></td>
        <td>${createdDisplay}</td>
        <td>${durationDisplay}</td>
        <td>
            <button class="btn-secondary" onclick="viewScanDetail('${scan.id}')">View</button>
            <button class="btn-danger" onclick="downloadScanRaw('${scan.id}')">Raw</button>
        </td>
    `;
}

function updateHistoryTable(scans) {
    const tbody = document.getElementById('historyBody');
    if (!tbody) return;

    const desiredOrder = scans.map(s => String(s.id));
    const scanMap = {};
    scans.forEach(s => { scanMap[String(s.id)] = s; });

    // Remove rows not present
    Array.from(tbody.querySelectorAll('tr[data-id]')).forEach(row => {
        const id = row.getAttribute('data-id');
        if (!(id in scanMap)) {
            tbody.removeChild(row);
        }
    });

    // Update/add rows and reorder
    desiredOrder.forEach(id => {
        let row = tbody.querySelector(`tr[data-id="${id.replace(/"/g, '\\"')}"]`);
        const scan = scanMap[id];
        if (!row) {
            row = document.createElement('tr');
            row.setAttribute('data-id', id);
            row.innerHTML = buildHistoryRowHtml(scan);
            tbody.appendChild(row);
        } else {
            const nextHtml = buildHistoryRowHtml(scan);
            if (row.innerHTML !== nextHtml) {
                row.innerHTML = nextHtml;
            }
        }
        tbody.appendChild(row);
    });
}

/**
 * Filter history based on search and filters
 */
function filterHistory() {
    const searchTerm = document.getElementById('searchScans').value.toLowerCase();
    const typeFilter = document.getElementById('filterType').value;
    const statusFilter = document.getElementById('filterStatus').value;

    const filtered = allScans.filter(scan => {
        const test = scan.test || {};
        const scanType = test.scan_type || '';
        const target = test.target || test.engagement_name || '';

        const matchesSearch = target.toLowerCase().includes(searchTerm);
        const matchesType = !typeFilter || scanType.includes(typeFilter);
        const statusNorm = ((test.status || '').toLowerCase() === 'failed' || (test.percent_complete && Number(test.percent_complete) < 100)) ? 'failed' : 'success';
        const matchesStatus = !statusFilter || (statusNorm === statusFilter);

        return matchesSearch && matchesType && matchesStatus;
    });

    displayHistoryTable(filtered);
}

/**
 * Get highest severity from findings list
 */
function getSeverity(findings) {
    const severityOrder = ['Critical', 'High', 'Medium', 'Low', 'Info'];
    if (!findings || findings.length === 0) return 'Info';

    for (const sev of severityOrder) {
        if (findings.some(f => f.severity === sev)) {
            return sev;
        }
    }
    return 'Info';
}

/**
 * View scan details
 */
async function viewScanDetail(scanId) {
    try {
        // scanId from onclick is a string, need to match with scan.id which is a number
        const scanIdNum = parseInt(scanId, 10);
        console.log('viewScanDetail called with:', scanId, 'parsed as:', scanIdNum);
        console.log('allScans available:', allScans.map(s => ({id: s.id, type: s.test.scan_type})));
        const scan = allScans.find(s => s.id === scanIdNum);
        if (!scan) {
            console.warn('Scan not found:', scanIdNum, 'Available:', allScans.map(s => s.id));
            showNotification('Scan not found', 'error');
            return;
        }
        console.log('Found scan:', scan);

        const test = scan.test || {};
        const findings = scan.findings || [];
        const percentComplete = Number(test.percent_complete || 100);
        const statusRaw = (test.status || '').toLowerCase();
        const status = statusRaw === 'failed' ? 'FAILED' : (percentComplete >= 100 ? 'SUCCESS' : 'FAILED');
        let durationDisplay = 'N/A';
        const start = test.start_date || test.created_on;
        const end = test.end_date;
        if (start && end) {
            const diff = Math.max(0, (new Date(end) - new Date(start)) / 1000);
            durationDisplay = formatDuration(diff) || 'N/A';
        } else if (test.estimated_time) {
            durationDisplay = formatDuration(test.estimated_time) || 'N/A';
        }

        // Build findings table
        let findingsHtml = `
            <div style="margin-bottom: 20px;">
                <h3 style="color: #2c3e50; margin-bottom: 15px;">
                    ${findings.length} Findings from ${getScanTypeLabel(test.scan_type || 'unknown')}
                </h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background-color: #ecf0f1;">
                        <tr>
                            <th style="padding: 10px; text-align: left; font-weight: 600;">Title</th>
                            <th style="padding: 10px; text-align: left; font-weight: 600;">Severity</th>
                            <th style="padding: 10px; text-align: left; font-weight: 600;">Date</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        findings.forEach(finding => {
            // Use scan start date for all findings, not the finding's individual date
            findingsHtml += `
                <tr style="border-bottom: 1px solid #ecf0f1;">
                    <td style="padding: 10px;">${finding.title}</td>
                    <td style="padding: 10px;">${getSeverityBadge(finding.severity)}</td>
                    <td style="padding: 10px;">${start ? formatDate(start) : 'N/A'}</td>
                </tr>
            `;
        });

        findingsHtml += `
                    </tbody>
                </table>
            </div>
        `;

        // Scan details
        let detailHtml = `
            <div style="margin-bottom: 20px;">
                <h3 style="color: #2c3e50;">Scan Details</h3>
                <table style="width: 100%; font-size: 14px;">
                    <tr>
                        <td style="width: 150px; font-weight: 600;">Target:</td>
                        <td>${test.target || test.engagement_name || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Type:</td>
                        <td>${getScanTypeLabel(test.scan_type || 'unknown')}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Status:</td>
                        <td>${getStatusBadge(status)}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Started:</td>
                        <td>${test.created_on ? formatDate(test.created_on) : 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Duration:</td>
                        <td>${durationDisplay}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Total Findings:</td>
                        <td><strong>${findings.length}</strong></td>
                    </tr>
                </table>
            </div>
        `;

        const modal = document.getElementById('scanDetailModal');
        document.getElementById('scanDetailContent').innerHTML = detailHtml + findingsHtml;
        modal.style.display = 'flex';

    } catch (error) {
        console.error('Error viewing scan detail:', error);
        showNotification('Error loading scan detail', 'error');
    }
}

/**
 * Close scan detail modal
 */
function closeScanDetail() {
    const modal = document.getElementById('scanDetailModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download raw scan results
 */
async function downloadScanRaw(scanId) {
    try {
        // scanId from onclick is a string, need to match with scan.id which is a number
        const scanIdNum = parseInt(scanId, 10);
        const scan = allScans.find(s => s.id === scanIdNum);
        if (!scan) {
            showNotification('Scan not found', 'error');
            return;
        }
        
        // For DefectDojo tests, use test ID from scan object
        const test = scan.test || {};
        const testId = test.id;
        if (!testId) {
            showNotification('Test ID not found', 'error');
            return;
        }
        
        // Try to download from backend endpoint that fetches from Dojo or MinIO
        const url = `${BACKEND_URL}/dojo/tests/${testId}/raw`;
        try {
            const response = await fetch(url);
            if (response.ok) {
                // Get filename from Content-Disposition header or use default
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = `test_${testId}_results.xml`;
                if (contentDisposition && contentDisposition.includes('filename=')) {
                    filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
                }
                
                const blob = await response.blob();
                const blobUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = blobUrl;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(blobUrl);
                document.body.removeChild(a);
                showNotification('Raw results downloaded', 'success');
            } else if (response.status === 404) {
                showNotification('Raw file not found in storage - findings may have been imported from DefectDojo without saving raw scan results', 'warning');
            } else {
                showNotification('Failed to download raw results', 'error');
            }
        } catch (error) {
            console.error('Error fetching raw file:', error);
            showNotification('Error downloading raw results', 'error');
        }
    } catch (error) {
        console.error('Error downloading raw results:', error);
        showNotification('Error downloading results', 'error');
    }
}
