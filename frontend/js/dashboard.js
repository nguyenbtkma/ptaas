// ========================================
// Dashboard Module
// ========================================

/**
 * Load and display dashboard
 */
async function loadDashboard() {
    try {
        // Load data in parallel
        const [findings, engagements, activeScans, tests] = await Promise.all([
            getFindings(1000),
            getEngagements(100),
            getActiveScans(),
            fetch('/api/dojo/tests?limit=1000').then(r => r.json()).catch(() => [])
        ]);

        // Calculate stats
        // Total Scans = number of tests completed (percent_complete = 100)
        const completedTests = tests.filter(t => t.percent_complete === 100).length;
        const totalScans = completedTests > 0 ? completedTests : tests.length;
        
        // Active Tasks = tests not completed + active scans in progress
        const incompleteTasks = tests.filter(t => t.percent_complete < 100).length;
        const activeTasks = incompleteTasks + (activeScans ? activeScans.length : 0);
        
        const totalFindings = findings.length;
        const criticalFindings = findings.filter(f => f.severity === 'Critical').length;

        // Update stat cards
        document.getElementById('totalScans').textContent = totalScans;
        document.getElementById('activeTasks').textContent = activeTasks;
        document.getElementById('totalFindings').textContent = totalFindings;
        document.getElementById('criticalFindings').textContent = criticalFindings;

        // Update recent findings table
        displayRecentFindings(findings.slice(0, 10));

        // Draw charts
        drawSeverityChart(findings);
        drawActivityChart(engagements);

        // Optionally show active scans list (if an element exists)
        const activeList = document.getElementById('activeScansList');
        if (activeList && activeScans && activeScans.length) {
            activeList.innerHTML = activeScans.map(s => `
                <li>${s.scan_type.toUpperCase()} — ${s.target} — ${s.status} (${s.progress || 0}%)</li>
            `).join('');
        }

    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Error loading dashboard', 'error');
    }
}

/**
 * Display recent findings in table
 */
function displayRecentFindings(findings) {
    const tbody = document.getElementById('recentFindings');
    tbody.innerHTML = '';

    if (findings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">No findings yet</td></tr>';
        return;
    }

    findings.forEach(finding => {
        const row = document.createElement('tr');
        const testTitle = finding.test_title || (finding.test && finding.test.title) || (finding.engagement_name) || 'N/A';
        row.innerHTML = `
            <td>${finding.title || 'Unknown'}</td>
            <td>${getSeverityBadge(finding.severity)}</td>
            <td>${testTitle}</td>
            <td>${formatDate(finding.date)}</td>
        `;
        row.style.cursor = 'pointer';
        row.onclick = () => showFindingDetail(finding);
        tbody.appendChild(row);
    });
}

/**
 * Draw severity distribution chart
 */
function drawSeverityChart(findings) {
    const canvas = document.getElementById('severityChart');
    if (!canvas || !findings.length) return;

    // Count by severity
    const severityCount = {
        'Critical': 0,
        'High': 0,
        'Medium': 0,
        'Low': 0,
        'Info': 0
    };

    findings.forEach(f => {
        if (f.severity in severityCount) {
            severityCount[f.severity]++;
        }
    });

    // Simple bar chart using HTML/CSS
    const html = `
        <div style="display: flex; flex-direction: column; gap: 15px;">
            ${Object.entries(severityCount).map(([severity, count]) => {
                const colors = {
                    'Critical': '#e74c3c',
                    'High': '#e67e22',
                    'Medium': '#f39c12',
                    'Low': '#3498db',
                    'Info': '#27ae60'
                };
                const percentage = findings.length ? (count / findings.length * 100) : 0;
                return `
                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style="font-weight: 600;">${severity}</span>
                            <span>${count}</span>
                        </div>
                        <div style="height: 20px; background-color: #ecf0f1; border-radius: 10px; overflow: hidden;">
                            <div style="height: 100%; background-color: ${colors[severity]}; width: ${percentage}%; transition: width 0.3s;"></div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;

    canvas.innerHTML = html;
}

/**
 * Draw activity chart (last 7 days)
 */
function drawActivityChart(engagements) {
    const canvas = document.getElementById('activityChart');
    if (!canvas) return;

    // Count scans by date (last 7 days)
    const now = new Date();
    const activityData = {};

    for (let i = 0; i < 7; i++) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        activityData[dateStr] = 0;
    }

    engagements.forEach(eng => {
        // Use created or updated timestamp (not target_start which is just a date)
        const dateField = eng.created || eng.updated;
        if (dateField) {
            const date = new Date(dateField);
            const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            if (dateStr in activityData) {
                activityData[dateStr]++;
            }
        }
    });

    const dates = Object.keys(activityData).reverse();
    const counts = dates.map(d => activityData[d]);
    const maxCount = Math.max(...counts, 1);

    const html = `
        <div style="display: flex; align-items: flex-end; gap: 10px; height: 200px;">
            ${dates.map((date, idx) => {
                const count = counts[idx];
                const height = (count / maxCount) * 100;
                return `
                    <div style="flex: 1; display: flex; flex-direction: column; align-items: center;">
                        <div style="width: 100%; height: ${height}%; background: linear-gradient(to top, #3498db, #2980b9); border-radius: 4px 4px 0 0; transition: all 0.3s;" title="${count} scans">
                        </div>
                        <span style="font-size: 12px; margin-top: 8px; text-align: center;">${date}</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;

    canvas.innerHTML = html;
}

/**
 * Show finding detail in modal
 */
async function showFindingDetail(finding) {
    try {
        const modal = document.getElementById('scanDetailModal');
        const content = document.getElementById('scanDetailContent');

        content.innerHTML = buildFindingDetail(finding);
        modal.style.display = 'flex';
    } catch (error) {
        console.error('Error showing finding detail:', error);
        showNotification('Error loading finding detail', 'error');
    }
}
