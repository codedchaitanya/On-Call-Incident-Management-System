// metrics.js - Metrics and analytics

const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', () => {
    // Set date filters to last 30 days by default
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    document.getElementById('metricsStartDate').valueAsDate = startDate;
    document.getElementById('metricsEndDate').valueAsDate = endDate;
});

async function loadMetrics() {
    const service = document.getElementById('metricsService').value || null;
    const startDate = document.getElementById('metricsStartDate').value || null;
    const endDate = document.getElementById('metricsEndDate').value || null;
    
    try {
        let url = `${API_BASE}/metrics/`;
        const params = new URLSearchParams();
        
        if (service) params.append('service_name', service);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        
        if (params.toString()) url += '?' + params.toString();
        
        const response = await fetch(url);
        const metrics = await response.json();
        
        renderMetrics(metrics);
    } catch (error) {
        console.error('Error loading metrics:', error);
        alert('Failed to load metrics');
    }
}

function renderMetrics(metrics) {
    const formatMinutes = (value) => {
        if (value === null || value === undefined) return '-';
        return value.toFixed(2) + ' min';
    };
    
    document.getElementById('mttaValue').textContent = formatMinutes(metrics.mtta_minutes);
    document.getElementById('mttrValue').textContent = formatMinutes(metrics.mttr_minutes);
    document.getElementById('totalIncidentsValue').textContent = metrics.total_incidents;
    document.getElementById('avgResponseValue').textContent = formatMinutes(metrics.avg_response_time);
    
    // Load recent incidents
    loadRecentIncidents();
}

async function loadRecentIncidents() {
    try {
        const response = await fetch(`${API_BASE}/incidents/list/all/`);
        const incidents = await response.json();
        
        const service = document.getElementById('metricsService').value || null;
        const startDate = new Date(document.getElementById('metricsStartDate').value);
        const endDate = new Date(document.getElementById('metricsEndDate').value);
        endDate.setDate(endDate.getDate() + 1);
        
        const filtered = incidents.filter(i => {
            if (i.status !== 'RESOLVED') return false;
            if (service && i.service_name !== service) return false;
            
            const created = new Date(i.created_at);
            if (created < startDate || created > endDate) return false;
            
            return true;
        });
        
        renderIncidentTimeline(filtered);
    } catch (error) {
        console.error('Error loading recent incidents:', error);
    }
}

function renderIncidentTimeline(incidents) {
    const container = document.getElementById('incidentTimelineContainer');
    
    if (!incidents || incidents.length === 0) {
        container.innerHTML = '<p class="text-gray-500">No incidents found</p>';
        return;
    }
    
    container.innerHTML = incidents.map(incident => {
        const created = new Date(incident.created_at);
        const acked = incident.acknowledged_at ? new Date(incident.acknowledged_at) : null;
        const resolved = incident.resolved_at ? new Date(incident.resolved_at) : null;
        
        const mtta = acked ? ((acked - created) / 60000).toFixed(2) : '-';
        const mttr = resolved ? ((resolved - created) / 60000).toFixed(2) : '-';
        
        return `
            <div class="border-l-4 border-blue-500 pl-4 py-2">
                <div class="flex justify-between items-start mb-1">
                    <div>
                        <p class="font-medium text-gray-900">${incident.title}</p>
                        <p class="text-sm text-gray-600">${incident.service_name} • ID: #${incident.id}</p>
                    </div>
                    <span class="text-xs text-gray-500">${created.toLocaleString()}</span>
                </div>
                <div class="flex gap-4 text-xs text-gray-600">
                    <span>MTTA: ${mtta} min</span>
                    <span>MTTR: ${mttr} min</span>
                    <span>Assigned: ${incident.assigned_to?.username || 'Unassigned'}</span>
                </div>
            </div>
        `;
    }).join('');
}

function resetMetricsFilters() {
    document.getElementById('metricsService').value = '';
    
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    document.getElementById('metricsStartDate').valueAsDate = startDate;
    document.getElementById('metricsEndDate').valueAsDate = endDate;
}
