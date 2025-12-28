// oncall.js - On-call schedule management

const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', () => {
    loadSchedules();
});

async function loadSchedules() {
    try {
        const response = await fetch(`${API_BASE}/oncall/schedules/`);
        const schedules = await response.json();
        renderSchedules(schedules);
    } catch (error) {
        console.error('Error loading schedules:', error);
    }
}

function renderSchedules(schedules) {
    const tbody = document.getElementById('schedulesTableBody');
    
    if (!schedules || schedules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-gray-500">No schedules found</td></tr>';
        return;
    }
    
    tbody.innerHTML = schedules.map(schedule => {
        const now = new Date();
        const startTime = new Date(schedule.start_time);
        const endTime = new Date(schedule.end_time);
        const isActive = now >= startTime && now <= endTime;
        const typeLabel = schedule.is_override ? '🔴 Override' : '🟢 Regular';
        const statusBadge = isActive ? '<span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">Active</span>' : '<span class="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs font-semibold">Inactive</span>';
        
        return `
            <tr class="hover:bg-gray-50 transition">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${schedule.service_name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${schedule.user.username}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${new Date(schedule.start_time).toLocaleString()}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${new Date(schedule.end_time).toLocaleString()}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">${typeLabel}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">${statusBadge}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                    <button onclick="deleteSchedule(${schedule.id})" class="text-red-600 hover:text-red-800 font-medium">
                        Delete
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function openScheduleModal() {
    document.getElementById('scheduleModal').classList.remove('hidden');
}

function closeScheduleModal() {
    document.getElementById('scheduleModal').classList.add('hidden');
    document.getElementById('scheduleForm').reset();
}

async function submitSchedule(event) {
    event.preventDefault();
    
    const serviceName = document.getElementById('scheduleService').value;
    const userId = document.getElementById('scheduleUserId').value;
    const startTime = new Date(document.getElementById('scheduleStartTime').value).toISOString();
    const endTime = new Date(document.getElementById('scheduleEndTime').value).toISOString();
    const isOverride = document.getElementById('scheduleOverride').checked;
    
    try {
        const response = await fetch(`${API_BASE}/oncall/schedules/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                service_name: serviceName,
                user_id: parseInt(userId),
                start_time: startTime,
                end_time: endTime,
                is_override: isOverride
            })
        });
        
        if (response.ok) {
            closeScheduleModal();
            loadSchedules();
            alert('Schedule created successfully');
        } else {
            const data = await response.json();
            alert('Error: ' + (data.detail || 'Failed to create schedule'));
        }
    } catch (error) {
        console.error('Error creating schedule:', error);
        alert('Failed to create schedule');
    }
}

async function deleteSchedule(scheduleId) {
    if (confirm('Are you sure you want to delete this schedule?')) {
        try {
            const response = await fetch(`${API_BASE}/oncall/schedules/${scheduleId}/`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                loadSchedules();
                alert('Schedule deleted successfully');
            } else {
                alert('Failed to delete schedule');
            }
        } catch (error) {
            console.error('Error deleting schedule:', error);
            alert('Failed to delete schedule');
        }
    }
}
