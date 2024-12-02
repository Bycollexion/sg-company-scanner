document.addEventListener('DOMContentLoaded', () => {
    const companiesTextarea = document.getElementById('companies');
    const searchBtn = document.getElementById('searchBtn');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsBody = document.getElementById('resultsBody');
    const spinner = searchBtn.querySelector('.spinner');
    const buttonText = searchBtn.querySelector('.button-text');

    // Auto-expand textarea
    companiesTextarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Handle search button click
    searchBtn.addEventListener('click', async () => {
        const companies = companiesTextarea.value
            .split('\n')
            .map(company => company.trim())
            .filter(company => company.length > 0);

        if (companies.length === 0) {
            alert('Please enter at least one company name');
            return;
        }

        if (companies.length > 50) {
            alert('Please enter no more than 50 companies');
            return;
        }

        // Show loading state
        searchBtn.disabled = true;
        spinner.classList.remove('hidden');
        buttonText.textContent = 'Searching...';
        resultsBody.innerHTML = '';
        resultsContainer.classList.add('hidden');

        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ companies }),
            });

            const results = await response.json();

            if (response.ok) {
                displayResults(results);
            } else {
                throw new Error(results.error || 'Failed to fetch results');
            }
        } catch (error) {
            console.error('Search error:', error);
            alert('An error occurred while searching. Please try again.');
        } finally {
            // Reset button state
            searchBtn.disabled = false;
            spinner.classList.add('hidden');
            buttonText.textContent = 'Search Companies';
        }
    });

    // Handle Shift+Enter to trigger search
    companiesTextarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            searchBtn.click();
        }
    });

    function displayResults(results) {
        resultsBody.innerHTML = '';
        
        results.forEach(result => {
            const row = document.createElement('tr');
            
            // Company Name
            const nameCell = document.createElement('td');
            nameCell.textContent = result.name;
            row.appendChild(nameCell);
            
            // Employee Count
            const employeeCell = document.createElement('td');
            if (result.error) {
                employeeCell.innerHTML = `<span class="error-message">${result.error}</span>`;
            } else {
                employeeCell.textContent = result.employee_count ? result.employee_count.toLocaleString() : 'N/A';
            }
            row.appendChild(employeeCell);
            
            // Location
            const locationCell = document.createElement('td');
            locationCell.textContent = result.location || 'N/A';
            row.appendChild(locationCell);
            
            // Source
            const sourceCell = document.createElement('td');
            sourceCell.textContent = result.source || 'N/A';
            row.appendChild(sourceCell);
            
            // LinkedIn URL
            const linkedinCell = document.createElement('td');
            if (result.linkedin_url) {
                const link = document.createElement('a');
                link.href = result.linkedin_url;
                link.textContent = 'View Profile';
                link.className = 'linkedin-link';
                link.target = '_blank';
                linkedinCell.appendChild(link);
            } else {
                linkedinCell.textContent = 'N/A';
            }
            row.appendChild(linkedinCell);
            
            resultsBody.appendChild(row);
        });
        
        resultsContainer.classList.remove('hidden');
    }
});
