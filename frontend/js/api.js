// ========================================
// API Helper - Communicate with Backend
// ========================================

const BACKEND_URL = 'http://localhost:8000';
// DefectDojo direct URLs are no longer called from browser (proxied via backend)
const DEFECTDOJO_URL = 'http://localhost:8080/api/v2';
const DEFECTDOJO_API_KEY = '56f6de75bd8329ced76366ad4e4c6d9a0f55e1dc';

// ===== SCAN APIs =====

/**
 * Start a new scan
 */
async function startScan(scanType, target, options) {
    try {
        const response = await fetch(`${BACKEND_URL}/scan/${scanType}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                target: target,
                options: options || ''
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error starting scan:', error);
        throw error;
    }
}

/**
 * Get scan status
 */
async function getScanStatus(taskId) {
    try {
        const response = await fetch(`${BACKEND_URL}/scan/status/${taskId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error getting scan status:', error);
        throw error;
    }
}

// ===== DEFECTDOJO APIs =====
/**
 * Get active scans (live status from backend)
 */
async function getActiveScans() {
    try {
        const response = await fetch(`${BACKEND_URL}/scan/active`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        return Array.isArray(data) ? data : [];
    } catch (error) {
        console.error('Error fetching active scans:', error);
        return [];
    }
}

/**
 * Get all findings (proxied through backend to avoid CORS)
 */
async function getFindings(limit = 100) {
    try {
        const response = await fetch(`${BACKEND_URL}/dojo/findings?limit=${limit}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        return Array.isArray(data) ? data : (data.results || data.value || []);
    } catch (error) {
        console.error('Error fetching findings:', error);
        return [];
    }
}

/**
 * Get finding detail (proxied)
 */
async function getFindingDetail(findingId) {
    try {
        const response = await fetch(`${BACKEND_URL}/results/${findingId}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error fetching finding detail:', error);
        throw error;
    }
}

/**
 * Get all products (proxied)
 */
async function getProducts(limit = 100) {
    try {
        const response = await fetch(`${BACKEND_URL}/dojo/products?limit=${limit}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        return Array.isArray(data) ? data : (data.results || data.value || []);
    } catch (error) {
        console.error('Error fetching products:', error);
        return [];
    }
}

/**
 * Get all engagements (scans) (proxied)
 */
async function getEngagements(limit = 100) {
    try {
        const response = await fetch(`${BACKEND_URL}/dojo/engagements?limit=${limit}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        return Array.isArray(data) ? data : (data.results || data.value || []);
    } catch (error) {
        console.error('Error fetching engagements:', error);
        return [];
    }
}

/**
 * Get test results for a specific test
 */
async function getTestResults(testId) {
    try {
        const response = await fetch(`${DEFECTDOJO_URL}/tests/${testId}/?include_findings=true`, {
            headers: {
                'Authorization': `Token ${DEFECTDOJO_API_KEY}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error fetching test results:', error);
        throw error;
    }
}

// ===== UTILITY APIs =====

/**
 * Get API health status
 */
async function getHealthStatus() {
    try {
        const response = await fetch(`${BACKEND_URL}/health`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error checking health:', error);
        return null;
    }
}

/**
 * Download raw results from MinIO
 */
async function downloadRawResults(taskId) {
    try {
        const response = await fetch(`${BACKEND_URL}/results/${taskId}/download`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        // Create blob from response
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `scan-${taskId}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error downloading results:', error);
        throw error;
    }
}

// ===== SCHEDULE APIs =====

/**
 * Create scheduled scan
 */
async function createSchedule(scheduleData) {
    try {
        const response = await fetch(`${BACKEND_URL}/schedule`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(scheduleData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error creating schedule:', error);
        throw error;
    }
}

/**
 * Get all schedules
 */
async function getSchedules() {
    try {
        const response = await fetch(`${BACKEND_URL}/schedule`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching schedules:', error);
        return [];
    }
}

/**
 * Delete schedule
 */
async function deleteSchedule(scheduleId) {
    try {
        const response = await fetch(`${BACKEND_URL}/schedule/${scheduleId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error deleting schedule:', error);
        throw error;
    }
}

// ===== ERROR HANDLING =====

function handleApiError(error, message) {
    console.error(message, error);
    alert(message + ': ' + error.message);
}
