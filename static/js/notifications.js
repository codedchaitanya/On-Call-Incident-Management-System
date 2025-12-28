/**
 * Notification System
 * Displays real-time alerts and status updates as toasts at bottom-right
 */

let notificationIdsShown = new Set();

/**
 * Fetch notifications from API and display them
 */
async function loadNotifications() {
    try {
        const response = await fetch('/api/notifications/');
        const data = await response.json();
        
        // Display new notifications
        data.notifications.forEach(notification => {
            if (!notificationIdsShown.has(notification.id)) {
                displayNotification(notification);
                notificationIdsShown.add(notification.id);
            }
        });
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

/**
 * Display a notification toast
 */
function displayNotification(notification) {
    const container = document.getElementById('notification-container');
    
    // Determine colors based on type
    let colors = {
        bg: 'bg-blue-50',
        border: 'border-blue-200',
        title: 'text-blue-900',
        icon: 'text-blue-500'
    };
    
    switch(notification.type) {
        case 'success':
            colors = {
                bg: 'bg-green-50',
                border: 'border-green-200',
                title: 'text-green-900',
                icon: 'text-green-500'
            };
            break;
        case 'error':
            colors = {
                bg: 'bg-red-50',
                border: 'border-red-200',
                title: 'text-red-900',
                icon: 'text-red-500'
            };
            break;
        case 'warning':
            colors = {
                bg: 'bg-yellow-50',
                border: 'border-yellow-200',
                title: 'text-yellow-900',
                icon: 'text-yellow-500'
            };
            break;
    }
    
    // Get icon emoji based on type
    let icon = '📢';
    if (notification.type === 'success') icon = '✅';
    else if (notification.type === 'error') icon = '❌';
    else if (notification.type === 'warning') icon = '⚠️';
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `notification-toast ${colors.bg} border ${colors.border} rounded-lg shadow-lg p-4 w-full max-w-sm`;
    toast.innerHTML = `
        <div class="flex items-start">
            <span class="text-2xl mr-3">${icon}</span>
            <div class="flex-1">
                <h3 class="${colors.title} font-bold text-sm">${notification.title}</h3>
                <p class="text-gray-700 text-xs mt-1">${notification.message}</p>
            </div>
            <button class="text-gray-400 hover:text-gray-600 ml-2 flex-shrink-0" onclick="this.closest('.notification-toast').remove();">×</button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto-dismiss if specified
    if (notification.auto_dismiss && notification.auto_dismiss > 0) {
        setTimeout(() => {
            if (toast.parentElement) {
                toast.classList.add('removing');
                setTimeout(() => toast.remove(), 300);
            }
        }, notification.auto_dismiss);
    }
}

/**
 * Send a custom notification
 */
function showNotification(title, message, type = 'info', autoDismiss = 5000) {
    displayNotification({
        id: Date.now(),
        title: title,
        message: message,
        type: type,
        timestamp: new Date().toISOString(),
        auto_dismiss: autoDismiss
    });
}

// Poll for notifications every 1 second
setInterval(loadNotifications, 1000);

// Initial load
loadNotifications();
