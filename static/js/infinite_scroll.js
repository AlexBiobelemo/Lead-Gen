document.addEventListener('DOMContentLoaded', function() {
    const leadsContainer = document.getElementById('leads-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Initialize currentPage from URL or default to 1
    const urlParams = new URLSearchParams(window.location.search);
    let currentPage = parseInt(urlParams.get('page')) || 1;
    
    let isLoading = false;
    let hasMore = true; // Assume true until proven otherwise by an AJAX call

    function loadMoreLeads() {
        if (isLoading || !hasMore || !loadingIndicator || !leadsContainer) return;

        isLoading = true;
        loadingIndicator.style.display = 'block';

        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('page', currentPage + 1);
        currentUrl.searchParams.set('ajax', '1'); // Indicate an AJAX request

        fetch(currentUrl.toString())
            .then(response => response.json())
            .then(data => {
                if (data.leads && data.leads.length > 0) {
                    data.leads.forEach(lead => {
                        const row = createLeadRow(lead);
                        if (leadsContainer) {
                            leadsContainer.appendChild(row);
                        }
                    });
                    currentPage++;
                    hasMore = data.has_more;
                } else {
                    hasMore = false;
                }
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                isLoading = false;
                // After loading, check if we still need to load more (e.g., if content is short)
                checkAndLoadMoreIfPageShort();
            })
            .catch(error => {
                console.error('Error loading more leads:', error);
                loadingIndicator.style.display = 'none';
                isLoading = false;
            });
    }

    function createLeadRow(lead) {
        const tr = document.createElement('tr');
        tr.classList.add('lead-dashboard-table-row'); // Add class for styling
        tr.innerHTML = `
            <td data-label="Select">
                <input type="checkbox" class="form-check-input lead-checkbox" value="${lead.id}">
            </td>
            <td data-label="Username">
                <strong>${lead.username}</strong>
                ${lead.tags_list && lead.tags_list.length > 0 ? `
                <br>
                <small>
                    ${lead.tags_list.map(tag => `<span class="badge bg-light text-dark">${tag}</span>`).join('')}
                </small>
                ` : ''}
            </td>
            <td data-label="Platform">
                <span class="badge bg-${lead.platform === 'instagram' ? 'danger' : lead.platform === 'twitter' ? 'info' : lead.platform === 'linkedin' ? 'primary' : 'secondary'}">
                    <i class="bi bi-${lead.platform === 'instagram' ? 'instagram' : lead.platform === 'twitter' ? 'twitter' : lead.platform === 'linkedin' ? 'linkedin' : 'globe'}"></i>
                    ${lead.platform.charAt(0).toUpperCase() + lead.platform.slice(1)}
                </span>
            </td>
            <td data-label="Full Name">${lead.full_name || '-'}</td>
            <td data-label="Followers">${lead.followers.toLocaleString()}</td>
            <td data-label="Engagement">
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar bg-${lead.engagement_score > 50 ? 'success' : lead.engagement_score > 25 ? 'warning' : 'danger'}"
                         role="progressbar"
                         aria-label="Engagement score: ${lead.engagement_score}%"
                         aria-valuenow="${lead.engagement_score}"
                         aria-valuemin="0"
                         aria-valuemax="100"
                         style="width: ${lead.engagement_score}%">
                        ${lead.engagement_score}%
                    </div>
                </div>
            </td>
            <td data-label="Location">${lead.location || '-'}</td>
            <td data-label="Actions">
                <div class="btn-group btn-group-sm">
                    <a href="/view-lead/${lead.id}" class="btn btn-outline-primary" title="View">
                        <i class="bi bi-eye"></i>
                    </a>
                    <a href="/ai-chat/${lead.id}" class="btn btn-outline-info" title="AI Chat">
                        <i class="bi bi-robot"></i>
                    </a>
                    <a href="/edit-lead/${lead.id}" class="btn btn-outline-success" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </a>
                    <button type="button" class="btn btn-outline-danger" onclick="deleteLead(${lead.id}, '${lead.username}')" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        `;
        return tr;
    }

    function checkAndLoadMoreIfPageShort() {
        if (document.documentElement.scrollHeight <= document.documentElement.clientHeight && hasMore && !isLoading) {
            loadMoreLeads();
        }
    }

    window.addEventListener('scroll', () => {
        const {
            scrollTop,
            scrollHeight,
            clientHeight
        } = document.documentElement;

        if (scrollTop + clientHeight >= scrollHeight - 100 && hasMore && !isLoading) {
            loadMoreLeads();
        }
    });

    // Initial load check
    checkAndLoadMoreIfPageShort();
});