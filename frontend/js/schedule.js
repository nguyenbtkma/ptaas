// ========================================
// Schedule Handler (added to index.html)
// ========================================

/**
 * Handle schedule form submission
 */
async function handleScheduleSubmit(e) {
    e.preventDefault();

    const scheduleName = document.getElementById('scheduleName').value;
    const scanType = document.getElementById('scheduleScanType').value;
    const target = document.getElementById('scheduleTarget').value;
    const frequency = document.getElementById('scheduleFrequency').value;
    const time = document.getElementById('scheduleTime').value;
    const email = document.getElementById('scheduleEmail').value;
    const notifyOn = document.getElementById('notifyOn').value;

    if (!scheduleName || !scanType || !target || !frequency || !time || !email) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }

    // Convert frequency + time to cron expression
    const [hours, minutes] = time.split(':');
    let cronExpression = `${minutes} ${hours}`;

    if (frequency === 'daily') {
        cronExpression += ' * * *';
    } else if (frequency === 'weekly') {
        cronExpression += ' * * 0';  // Sunday
    } else if (frequency === 'monthly') {
        cronExpression += ' 1 * *';  // First day of month
    }

    try {
        const submitBtn = document.querySelector('#scheduleForm button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';

        // Create schedule via API
        const response = await createSchedule({
            name: scheduleName,
            scan_type: scanType,
            target: target,
            schedule_cron: cronExpression,
            email: email,
            notify_on: notifyOn
        });

        showNotification('Schedule created successfully!', 'success');
        hideScheduleForm();
        loadScheduleList();

        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Schedule';

    } catch (error) {
        console.error('Error creating schedule:', error);
        showNotification('Error creating schedule: ' + error.message, 'error');

        const submitBtn = document.querySelector('#scheduleForm button[type="submit"]');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Schedule';
    }
}

/**
 * Load and display scheduled scans
 */
async function loadScheduleList() {
    try {
        setTableLoading('scheduleBody', 'Loading schedules...');

        const schedules = await getSchedules();

        displayScheduleTable(schedules);

    } catch (error) {
        console.error('Error loading schedules:', error);
        // If API doesn't exist yet, just show empty state
        document.getElementById('scheduleBody').innerHTML = 
            '<tr><td colspan="7" class="loading">No scheduled scans yet. Create one to get started!</td></tr>';
    }
}

/**
 * Display schedules in table
 */
function displayScheduleTable(schedules) {
    const tbody = document.getElementById('scheduleBody');
    tbody.innerHTML = '';

    if (!schedules || schedules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No scheduled scans yet. Create one to get started!</td></tr>';
        return;
    }

    schedules.forEach(schedule => {
        const nextRun = schedule.next_run ? formatDate(schedule.next_run) : 'N/A';
        const isActive = schedule.is_active ? '✓ Active' : '⊗ Inactive';

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${schedule.name}</strong></td>
            <td>${getScanTypeIcon(schedule.scan_type)} ${getScanTypeLabel(schedule.scan_type)}</td>
            <td>${schedule.target}</td>
            <td>${schedule.schedule_cron || 'N/A'}</td>
            <td>${nextRun}</td>
            <td>${isActive}</td>
            <td>
                <button class="btn-secondary" onclick="editSchedule(${schedule.id})">Edit</button>
                <button class="btn-danger" onclick="deleteScheduleItem(${schedule.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Edit schedule (placeholder)
 */
function editSchedule(scheduleId) {
    showNotification('Edit functionality coming soon', 'info');
}

/**
 * Delete scheduled scan
 */
async function deleteScheduleItem(scheduleId) {
    if (!confirm('Are you sure you want to delete this schedule?')) {
        return;
    }

    try {
        await deleteSchedule(scheduleId);
        showNotification('Schedule deleted', 'success');
        loadScheduleList();
    } catch (error) {
        console.error('Error deleting schedule:', error);
        showNotification('Error deleting schedule', 'error');
    }
}
