from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup
import requests
import random
import time
import json
import os
import logging
import traceback
from urllib.parse import quote_plus
import concurrent.futures
import threading
from fake_useragent import UserAgent
import re

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
logger = app.logger

# Thread-local storage for session
thread_local = threading.local()

def get_random_user_agent():
    try:
        ua = UserAgent()
        return ua.random
    except:
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

def make_request(url, max_retries=3):
    session = get_session()
    headers = {'User-Agent': get_random_user_agent()}
    
    for attempt in range(max_retries):
        try:
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            time.sleep(random.uniform(1, 3))  # Random delay between requests
            return response.text
        except Exception as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(random.uniform(2, 5))  # Longer delay between retries

def extract_employee_count(text):
    # Common patterns for employee counts
    patterns = [
        r'(\d{1,3}(?:,\d{3})*(?:\+)?)\s*(?:employees?|staff|people)',
        r'(\d{1,3}(?:,\d{3})*(?:\+)?)\s*(?:workers?|members?)',
        r'(?:team size|company size|employees?|staff size).*?(\d{1,3}(?:,\d{3})*(?:\+)?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count = match.group(1).replace(',', '')
            if count.endswith('+'):
                count = count[:-1]
            return int(count)
    return None

def search_company(company_name):
    logger.info(f"Searching for company: {company_name}")
    try:
        # Search LinkedIn
        search_url = f"https://www.google.com/search?q={quote_plus(f'{company_name} singapore site:linkedin.com/company')}"
        html_content = make_request(search_url)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        search_results = soup.find_all('div', class_='g')
        
        company_data = {
            'name': company_name,
            'employee_count': None,
            'location': None,
            'source': None,
            'linkedin_url': None
        }
        
        for result in search_results:
            link = result.find('a')
            if not link:
                continue
                
            url = link['href']
            if 'linkedin.com/company/' in url:
                company_data['linkedin_url'] = url
                try:
                    page_content = make_request(url)
                    page_soup = BeautifulSoup(page_content, 'html.parser')
                    
                    # Try to find employee count
                    employee_text = page_soup.find(text=re.compile(r'\d+(?:,\d{3})*\+?\s*employees', re.IGNORECASE))
                    if employee_text:
                        count = extract_employee_count(employee_text)
                        if count:
                            company_data['employee_count'] = count
                            company_data['source'] = 'LinkedIn'
                    
                    # Try to find location
                    location_elem = page_soup.find('div', text=re.compile('Singapore', re.IGNORECASE))
                    if location_elem:
                        company_data['location'] = 'Singapore'
                    
                except Exception as e:
                    logger.error(f"Error processing LinkedIn page: {str(e)}")
                
                break
        
        if not company_data['employee_count']:
            # Try Google search as fallback
            search_url = f"https://www.google.com/search?q={quote_plus(f'{company_name} singapore number of employees')}"
            html_content = make_request(search_url)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for employee count in search results
            for result in soup.find_all(['div', 'span', 'p']):
                text = result.get_text()
                count = extract_employee_count(text)
                if count:
                    company_data['employee_count'] = count
                    company_data['source'] = 'Google Search'
                    break
        
        return company_data
        
    except Exception as e:
        logger.error(f"Error searching for {company_name}: {str(e)}")
        return {
            'name': company_name,
            'error': str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_companies():
    try:
        data = request.get_json()
        logger.info(f"Received search request: {data}")
        
        if not data or 'companies' not in data:
            return jsonify({"error": "No companies provided"}), 400
        
        companies = data['companies']
        logger.info(f"Processing companies: {companies}")
        
        # Remove duplicates and empty strings
        companies = list(set(filter(None, [c.strip() for c in companies])))
        
        # Limit to 50 companies at once
        companies = companies[:50]
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_company = {executor.submit(search_company, company): company for company in companies}
            for future in concurrent.futures.as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    result = future.result()
                    logger.info(f"Search result for {company}: {result}")
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing company {company}: {str(e)}")
                    results.append({
                        'name': company,
                        'error': str(e)
                    })
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port)
