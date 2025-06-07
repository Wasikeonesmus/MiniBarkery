function submitAddStock() {
    const form = document.getElementById('addStockForm');
    const formData = new FormData(form);

    fetch('/inventory/add-stock', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            location.reload(); // Refresh the page to show updated stock
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while adding stock');
    });
}

function adjustStock(productId) {
    // Open a modal for stock adjustment
    const modal = new bootstrap.Modal(document.getElementById('adjustStockModal'));
    const form = document.getElementById('adjustStockForm');
    form.querySelector('input[name="product_id"]').value = productId;
    modal.show();
}

function viewHistory(productId) {
    // Redirect to stock history page
    window.location.href = `/inventory/history/${productId}`;
}

function reorderProduct(productId) {
    // Send an AJAX request to trigger reorder process
    fetch(`/inventory/reorder/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Reorder request sent successfully');
        } else {
            alert('Failed to send reorder request: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while processing the reorder request');
    });
}

function exportInventory() {
    // Trigger inventory export
    window.location.href = '/inventory/export';
}

function submitAdjustStock() {
    const form = document.getElementById('adjustStockForm');
    const formData = new FormData(form);
    const productId = formData.get('product_id');

    fetch(`/inventory/adjust-stock/${productId}`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Stock adjusted successfully');
            location.reload(); // Refresh the page to show updated stock
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while adjusting stock');
    });
}

// Mobile-friendly inventory management

// Prevent default zoom on input focus for iOS
function preventZoom() {
    const viewportMeta = document.querySelector('meta[name="viewport"]');
    if (viewportMeta) {
        viewportMeta.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
    }
}

// Touch-friendly stock adjustment
function initTouchFriendlyStockAdjustment() {
    const adjustButtons = document.querySelectorAll('[data-adjust-stock]');
    
    adjustButtons.forEach(button => {
        // Add touch and click event listeners
        button.addEventListener('touchstart', function(e) {
            e.preventDefault(); // Prevent default touch behavior
            const productId = this.getAttribute('data-product-id');
            openStockAdjustmentModal(productId);
        });

        button.addEventListener('click', function() {
            const productId = this.getAttribute('data-product-id');
            openStockAdjustmentModal(productId);
        });
    });
}

// Open stock adjustment modal
function openStockAdjustmentModal(productId) {
    const modal = new bootstrap.Modal(document.getElementById('adjustStockModal'));
    const productIdInput = document.getElementById('adjustProductId');
    
    if (productIdInput) {
        productIdInput.value = productId;
    }
    
    modal.show();
}

// Responsive form submission
function initResponsiveFormSubmission() {
    const forms = document.querySelectorAll('form[data-ajax-submit]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const url = this.getAttribute('action');
            
            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show toast or alert
                    showMobileNotification('Stock updated successfully', 'success');
                    // Optionally reload or update UI
                    location.reload();
                } else {
                    showMobileNotification(data.message || 'Error updating stock', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMobileNotification('Network error. Please try again.', 'error');
            });
        });
    });
}

// Mobile-friendly notifications
function showMobileNotification(message, type = 'info') {
    // Create a toast-like notification
    const notification = document.createElement('div');
    notification.className = `mobile-notification mobile-notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Automatically remove after 3 seconds
    setTimeout(() => {
        notification.classList.add('mobile-notification-hide');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 3000);
}

// Add mobile-specific styles
function addMobileStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .mobile-notification {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0,0,0,0.8);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            z-index: 9999;
            transition: opacity 0.5s ease;
            max-width: 90%;
            text-align: center;
        }
        
        .mobile-notification-success {
            background-color: rgba(40, 167, 69, 0.9);
        }
        
        .mobile-notification-error {
            background-color: rgba(220, 53, 69, 0.9);
        }
        
        .mobile-notification-hide {
            opacity: 0;
        }
    `;
    document.head.appendChild(style);
}

// Initialize mobile-friendly features
function initMobileInventory() {
    preventZoom();
    initTouchFriendlyStockAdjustment();
    initResponsiveFormSubmission();
    addMobileStyles();
}

// Run initialization when DOM is fully loaded
document.addEventListener('DOMContentLoaded', initMobileInventory); 