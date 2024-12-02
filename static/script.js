// Auto-resize textarea
const textarea = document.getElementById('companyInput');
textarea.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Handle Shift+Enter shortcut
textarea.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.shiftKey) {
        e.preventDefault();
        searchCompanies();
    }
});

function showNotification(message, isError = false) {
    const notification = document.createElement('div');
    notification.className = `notification ${isError ? 'error' : ''}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function formatNumber(num) {
    return typeof num === 'number' ? num.toLocaleString() : num;
}

function createSourceBadge(source, isMain = false) {
    const badge = document.createElement('span');
    badge.className = `source-badge ${source.toLowerCase()}-badge ${isMain ? 'main-source' : ''}`;
    badge.textContent = source;
    return badge;
}

function createOtherSourcesTooltip(sources) {
    if (!sources || sources.length === 0) return '';
    
    return sources.map(source => {
        return `${source.source}: ${formatNumber(source.count)} ${source.is_sg ? '(SG)' : '(Global)'}`;
    }).join('\n');
}

function searchCompanies() {
    const companies = textarea.value.trim().split('\n').filter(company => company.trim());
    
    if (companies.length === 0) {
        showNotification('Please enter at least one company name', true);
        return;
    }

    if (companies.length > 50) {
        showNotification('Maximum 50 companies allowed at once', true);
        return;
    }

    // Show loading state
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    document.getElementById('noResults').style.display = 'none';
    document.getElementById('searchButton').disabled = true;

    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ companies }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.length === 0) {
            document.getElementById('noResults').style.display = 'block';
            return;
        }

        const resultsBody = document.getElementById('resultsBody');
        resultsBody.innerHTML = '';

        data.forEach(result => {
            const row = document.createElement('tr');
            
            // Company name
            const nameCell = document.createElement('td');
            nameCell.textContent = result.company;
            row.appendChild(nameCell);
            
            // Employee count
            const countCell = document.createElement('td');
            countCell.textContent = formatNumber(result.employee_count);
            row.appendChild(countCell);
            
            // Region
            const regionCell = document.createElement('td');
            const badge = document.createElement('span');
            badge.className = `badge ${result.is_sg ? 'sg-badge' : 'global-badge'}`;
            badge.textContent = result.is_sg ? 'Singapore' : 'Global';
            regionCell.appendChild(badge);
            row.appendChild(regionCell);
            
            // Main source
            const sourceCell = document.createElement('td');
            const sourceLink = document.createElement('a');
            sourceLink.href = result.url;
            sourceLink.target = '_blank';
            sourceLink.appendChild(createSourceBadge(result.source, true));
            sourceCell.appendChild(sourceLink);
            row.appendChild(sourceCell);
            
            // Other sources
            const otherSourcesCell = document.createElement('td');
            if (result.other_sources && result.other_sources.length > 0) {
                const sourcesContainer = document.createElement('div');
                sourcesContainer.className = 'other-sources';
                
                result.other_sources.forEach(source => {
                    const sourceBadge = createSourceBadge(source.source);
                    sourceBadge.title = `${formatNumber(source.count)} ${source.is_sg ? '(SG)' : '(Global)'}`;
                    sourcesContainer.appendChild(sourceBadge);
                });
                
                otherSourcesCell.appendChild(sourcesContainer);
            } else {
                otherSourcesCell.textContent = 'None';
            }
            row.appendChild(otherSourcesCell);
            
            resultsBody.appendChild(row);
        });

        document.getElementById('results').style.display = 'block';
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while searching', true);
    })
    .finally(() => {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('searchButton').disabled = false;
    });
}
