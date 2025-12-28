// dashboard.js - Incident Dashboard functionality

const API_BASE = '/api';
let allIncidents = [];

// Load incidents on page load
document.addEventListener('DOMContentLoaded', () => {
    loadIncidents();
    // Refresh every 10 seconds
    setInterval(loadIncidents, 10000);
});

async function loadIncidents() {
    try {
        const response = await fetch(`${API_BASE}/incidents/list/all/`);
        const incidents = await response.json();
        allIncidents = incidents;
        
        // Apply filters
        const statusFilter = document.getElementById('statusFilter').value.trim();
        const serviceFilter = document.getElementById('serviceFilter').value.trim().toLowerCase();
        
        let filteredIncidents = incidents.filter(incident => {
            const matchStatus = !statusFilter || incident.status === statusFilter;
            const matchService = !serviceFilter || incident.service_name.toLowerCase().includes(serviceFilter);
            return matchStatus && matchService;
        });
        
        renderIncidents(filteredIncidents);
    } catch (error) {
        console.error('Error loading incidents:', error);
        showError('Failed to load incidents');
    }
}

function renderIncidents(incidents) {
    const tbody = document.getElementById('incidentsTableBody');
    
    if (!incidents || incidents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-gray-500">No incidents found</td></tr>';
        return;
    }
    
    tbody.innerHTML = incidents.map(incident => {
        const statusColor = getStatusColor(incident.status);
        const createdAt = new Date(incident.created_at).toLocaleString();
        const assignedTo = incident.assigned_to?.username || 'Unassigned';
        
        return `
            <tr class="hover:bg-gray-50 transition">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">#${incident.id}</td>
                <td class="px-6 py-4 text-sm text-gray-900">
                    <button onclick="showDetails(${incident.id})" class="text-blue-600 hover:text-blue-800 font-medium">
                        ${incident.title}
                    </button>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${incident.service_name}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColor}">
                        ${incident.status}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${assignedTo}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${createdAt}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                    <button onclick="openStatusModal(${incident.id})" class="text-blue-600 hover:text-blue-800 font-medium">
                        Update
                    </button>
                    <button onclick="showDetails(${incident.id})" class="text-gray-600 hover:text-gray-800 font-medium">
                        View
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function getStatusColor(status) {
    const colors = {
        'TRIGGERED': 'bg-red-100 text-red-800',
        'ACKNOWLEDGED': 'bg-yellow-100 text-yellow-800',
        'ESCALATED': 'bg-orange-100 text-orange-800',
        'RESOLVED': 'bg-green-100 text-green-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
}

function openStatusModal(incidentId) {
    document.getElementById('selectedIncidentId').value = incidentId;
    document.getElementById('statusModal').classList.remove('hidden');
}

function closeStatusModal() {
    document.getElementById('statusModal').classList.add('hidden');
}

async function transitionIncident(action) {
    const incidentId = document.getElementById('selectedIncidentId').value;
    const endpoint = `${API_BASE}/incidents/${incidentId}/${action}/`;
    
    try {
        const response = await fetch(endpoint, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(`Incident ${action}ed successfully`);
            closeStatusModal();
            loadIncidents();
        } else {
            showError(data.detail || `Failed to ${action} incident`);
        }
    } catch (error) {
        console.error(`Error ${action}ing incident:`, error);
        showError(`Failed to ${action} incident`);
    }
}

function showDetails(incidentId) {
    const incident = allIncidents.find(i => i.id === incidentId);
    if (!incident) return;
    
    const detailsContent = document.getElementById('detailsContent');
    const createdAt = new Date(incident.created_at).toLocaleString();
    const acknowledgedAt = incident.acknowledged_at ? new Date(incident.acknowledged_at).toLocaleString() : 'N/A';
    const resolvedAt = incident.resolved_at ? new Date(incident.resolved_at).toLocaleString() : 'N/A';
    const escalatedAt = incident.escalated_at ? new Date(incident.escalated_at).toLocaleString() : 'N/A';
    
    detailsContent.innerHTML = `
        <div class="space-y-4">
            <div class="border-b pb-4">
                <h4 class="text-lg font-bold text-gray-900 mb-2">${incident.title}</h4>
                <p class="text-gray-600">${incident.description}</p>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <p class="text-xs text-gray-500 uppercase">ID</p>
                    <p class="font-mono text-sm text-gray-900">#${incident.id}</p>
                </div>
                <div>
                    <p class="text-xs text-gray-500 uppercase">Service</p>
                    <p class="text-sm text-gray-900">${incident.service_name}</p>
                </div>
                <div>
                    <p class="text-xs text-gray-500 uppercase">Status</p>
                    <span class="px-2 py-1 text-xs font-semibold rounded ${getStatusColor(incident.status)}">
                        ${incident.status}
                    </span>
                </div>
                <div>
                    <p class="text-xs text-gray-500 uppercase">Assigned To</p>
                    <p class="text-sm text-gray-900">${incident.assigned_to?.username || 'Unassigned'}</p>
                </div>
            </div>
            
            <div class="bg-gray-50 rounded p-4 space-y-2">
                <p class="text-sm"><span class="font-medium text-gray-700">Created:</span> ${createdAt}</p>
                <p class="text-sm"><span class="font-medium text-gray-700">Acknowledged:</span> ${acknowledgedAt}</p>
                <p class="text-sm"><span class="font-medium text-gray-700">Resolved:</span> ${resolvedAt}</p>
                <p class="text-sm"><span class="font-medium text-gray-700">Escalated:</span> ${escalatedAt}</p>
            </div>
            
            <div class="flex gap-2 pt-4">
                <button onclick="openStatusModal(${incident.id})" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium">
                    Update Status
                </button>
                <button onclick="closeDetailsModal()" class="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-900 px-4 py-2 rounded-lg font-medium">
                    Close
                </button>
            </div>
        </div>
    `;
    
    document.getElementById('detailsModal').classList.remove('hidden');
}

function closeDetailsModal() {
    document.getElementById('detailsModal').classList.add('hidden');
}

function showError(message) {
    console.error(message);
    // Could show a toast or alert
}

function showSuccess(message) {
    console.log('✅', message);
    // Could show a toast
}
