// Custom JavaScript for Lead Generation App

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Add fade-in animation to cards
    var cards = document.querySelectorAll('.card');
    cards.forEach(function(card, index) {
        setTimeout(function() {
            card.classList.add('fade-in');
        }, index * 50);
    });
});

// Function to show/hide loading spinner on a button
function toggleLoadingSpinner(buttonElement, isLoading) {
    if (isLoading) {
        buttonElement.classList.add('loading');
        buttonElement.setAttribute('disabled', 'true');
    } else {
        buttonElement.classList.remove('loading');
        buttonElement.removeAttribute('disabled');
    }
}

// Confirm before deleting
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

// Copy to clipboard function
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copied to clipboard!', 'success');
    }).catch(function(err) {
        showToast('Failed to copy', 'error');
    });
}

// Show toast notification
function showToast(message, type = 'info') {
    var toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '11';
        document.body.appendChild(toastContainer);
    }

    var toastId = 'toast-' + Date.now();
    var bgColor = type === 'success' ? 'bg-success' : 
                  type === 'error' ? 'bg-danger' : 
                  type === 'warning' ? 'bg-warning' : 'bg-info';

    var toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgColor} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    var toastElement = document.getElementById(toastId);
    var toast = new bootstrap.Toast(toastElement);
    toast.show();

    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Form validation
function validateForm(formId) {
    var form = document.getElementById(formId);
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    }
}

// Format number with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Live search functionality
function initLiveSearch(inputId, resultsId) {
    var input = document.getElementById(inputId);
    if (input) {
        input.addEventListener('input', debounce(function(e) {
            var query = e.target.value;
            // Implement AJAX search here
            console.log('Searching for:', query);
        }, 300));
    }
}

// Table row selection
function initTableSelection() {
    var selectAllCheckbox = document.getElementById('selectAll');
    var rowCheckboxes = document.querySelectorAll('.lead-checkbox');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            rowCheckboxes.forEach(function(checkbox) {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateBulkActions();
        });
    }

    rowCheckboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            updateBulkActions();
            updateSelectAll();
        });
    });
}

// Update bulk action buttons based on selection
function updateBulkActions() {
    var checkedCount = document.querySelectorAll('.lead-checkbox:checked').length;
    var bulkActionsBtn = document.getElementById('bulkDeleteBtn');
    
    if (bulkActionsBtn) {
        if (checkedCount > 0) {
            bulkActionsBtn.style.display = 'inline-block';
            bulkActionsBtn.textContent = `Delete ${checkedCount} selected`;
        } else {
            bulkActionsBtn.style.display = 'none';
        }
    }
}

// Update select all checkbox state
function updateSelectAll() {
    var selectAllCheckbox = document.getElementById('selectAll');
    var rowCheckboxes = document.querySelectorAll('.lead-checkbox');
    var checkedCount = document.querySelectorAll('.lead-checkbox:checked').length;

    if (selectAllCheckbox) {
        selectAllCheckbox.checked = checkedCount === rowCheckboxes.length;
        selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < rowCheckboxes.length;
    }
}

// Export selected leads
function exportSelected() {
    var selectedIds = [];
    document.querySelectorAll('.lead-checkbox:checked').forEach(function(checkbox) {
        selectedIds.push(checkbox.value);
    });

    if (selectedIds.length === 0) {
        showToast('Please select at least one lead', 'warning');
        return;
    }

    // Create form and submit
    var form = document.createElement('form');
    form.method = 'POST';
    form.action = '/export-selected';
    
    selectedIds.forEach(function(id) {
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'lead_ids[]';
        input.value = id;
        form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
}

// Bulk delete selected leads
function bulkDeleteSelected() {
    var selectedIds = [];
    document.querySelectorAll('.lead-checkbox:checked').forEach(function(checkbox) {
        selectedIds.push(checkbox.value);
    });

    if (selectedIds.length === 0) {
        showToast('Please select at least one lead', 'warning');
        return;
    }

    if (confirm(`Are you sure you want to delete ${selectedIds.length} leads? This action cannot be undone.`)) {
        // Submit delete request
        fetch('/api/leads/bulk-delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ lead_ids: selectedIds })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showToast(data.error || 'Failed to delete leads', 'error');
            }
        })
        .catch(error => {
            showToast('An error occurred', 'error');
            console.error('Error:', error);
        });
    }
}

// API request helper
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Load statistics
async function loadStats() {
    try {
        const data = await apiRequest('/api/stats');
        if (data.success) {
            // Update UI with stats
            console.log('Stats loaded:', data.data);
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Auto-save form (draft functionality)
function initAutoSave(formId) {
    var form = document.getElementById(formId);
    if (!form) return;

    var inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(function(input) {
        input.addEventListener('change', function() {
            var formData = new FormData(form);
            var data = Object.fromEntries(formData);
            localStorage.setItem('draft_' + formId, JSON.stringify(data));
            showToast('Draft saved', 'info');
        });
    });

    // Load draft on page load
    var draft = localStorage.getItem('draft_' + formId);
    if (draft) {
        try {
            var data = JSON.parse(draft);
            Object.keys(data).forEach(function(key) {
                var input = form.querySelector('[name="' + key + '"]');
                if (input) {
                    input.value = data[key];
                }
            });
        } catch (error) {
            console.error('Failed to load draft:', error);
        }
    }
}

// Clear draft
function clearDraft(formId) {
    localStorage.removeItem('draft_' + formId);
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for quick search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        var searchInput = document.querySelector('input[name="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Ctrl/Cmd + N for new lead
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        window.location.href = '/add-lead';
    }

    // Escape to close modals
    if (e.key === 'Escape') {
        var modals = document.querySelectorAll('.modal.show');
        modals.forEach(function(modal) {
            bootstrap.Modal.getInstance(modal)?.hide();
        });
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initTableSelection();
    
    // Attach bulk delete event
    var bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', bulkDeleteSelected);
    }

    // AI Chat specific button loading
    const generateEmailBtn = document.getElementById('generateEmailBtn');
    const emailGenerationForm = document.getElementById('emailGenerationForm');
    const generateEmailContentBtn = document.getElementById('generateEmailContentBtn');

    if (generateEmailBtn) {
        generateEmailBtn.addEventListener('click', function() {
            // No spinner needed for just opening the modal
        });
    }

    if (emailGenerationForm) {
        emailGenerationForm.addEventListener('submit', function() {
            toggleLoadingSpinner(generateEmailContentBtn, true);
        });
    }

    // Intercept fetch calls for email generation to hide spinner
    const originalFetch = window.fetch;
    window.fetch = function() {
        return originalFetch.apply(this, arguments).then(response => {
            // Check if the fetch call is for email generation
            if (Array.from(arguments).includes('/generate-email-content')) {
                toggleLoadingSpinner(generateEmailContentBtn, false);
            }
            return response;
        }).catch(error => {
            if (Array.from(arguments).includes('/generate-email-content')) {
                toggleLoadingSpinner(generateEmailContentBtn, false);
            }
            throw error;
        });
    };
});

// Progress bar animation
function animateProgressBars() {
    var progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(function(bar) {
        var width = bar.style.width;
        bar.style.width = '0';
        setTimeout(function() {
            bar.style.width = width;
        }, 100);
    });
}

// Call on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', animateProgressBars);
} else {
    animateProgressBars();
}

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Add scroll to top button
window.addEventListener('scroll', function() {
    var scrollBtn = document.getElementById('scrollTopBtn');
    if (scrollBtn) {
        if (window.pageYOffset > 300) {
            scrollBtn.style.display = 'block';
        } else {
            scrollBtn.style.display = 'none';
        }
    }
});
