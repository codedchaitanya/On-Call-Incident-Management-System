// trigger.js - Incident trigger functionality

const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', () => {
    // Auto-populate service from URL param if provided
    const params = new URLSearchParams(window.location.search);
    const service = params.get('service');
    if (service) {
        document.getElementById('serviceName').value = service;
    }
});

function setService(serviceName) {
    document.getElementById('serviceName').value = serviceName;
    document.getElementById('serviceName').focus();
}

async function submitIncident(event) {
    event.preventDefault();
    
    const serviceName = document.getElementById('serviceName').value.trim();
    const title = document.getElementById('title').value.trim();
    const description = document.getElementById('description').value.trim();
    
    if (!serviceName || !title) {
        showError('Service name and title are required');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/incidents/trigger/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                service_name: serviceName,
                title: title,
                description: description
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(data);
            // Reset form
            document.getElementById('triggerForm').reset();
        } else {
            showError(data.detail || 'Failed to trigger incident');
        }
    } catch (error) {
        console.error('Error triggering incident:', error);
        showError('Failed to trigger incident');
    }
}

function showSuccess(incident) {
    document.getElementById('triggerForm').classList.add('hidden');
    document.getElementById('successMessage').classList.remove('hidden');
    
    const assignedTo = incident.assigned_to?.username || 'UNASSIGNED';
    document.getElementById('incidentInfo').innerHTML = `
        <p><strong>Incident ID:</strong> #${incident.id}</p>
        <p><strong>Service:</strong> ${incident.service_name}</p>
        <p><strong>Title:</strong> ${incident.title}</p>
        <p><strong>Status:</strong> ${incident.status}</p>
        <p><strong>Assigned To:</strong> ${assignedTo}</p>
        <div class="mt-4 flex gap-2">
            <a href="/" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium text-center">
                View Dashboard
            </a>
            <button onclick="resetForm()" class="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-900 px-4 py-2 rounded-lg font-medium">
                Trigger Another
            </button>
        </div>
    `;
}

function showError(message) {
    document.getElementById('errorMessage').classList.remove('hidden');
    document.getElementById('errorText').textContent = message;
    
    // Hide after 5 seconds
    setTimeout(() => {
        document.getElementById('errorMessage').classList.add('hidden');
    }, 5000);
}

function resetForm() {
    document.getElementById('triggerForm').classList.remove('hidden');
    document.getElementById('successMessage').classList.add('hidden');
    document.getElementById('triggerForm').reset();
}
