from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup, SoupStrainer
import requests
from fake_useragent import UserAgent
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import random
import time
import json
import os
import json
from pathlib import Path
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys

app = Flask(__name__)
thread_local = threading.local()

LEADERBOARD_FILE = 'leaderboard.json'

def load_leaderboard():
    try:
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_leaderboard(scores):
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(scores, f)

def get_session():
    if not hasattr(thread_local, "session"):
        session = requests.Session()
        
        # More realistic user agents
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Edge/119.0.0.0'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"'
        }
        
        session.headers.update(headers)
        
        # Configure retry strategy with longer delays
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
        )
        
        # Configure connection pooling and timeouts
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        thread_local.session = session
    
    return thread_local.session

def find_employee_count(text):
    """Extract employee count from text using various patterns."""
    employee_patterns = [
        r'([\d,\.]+)[\+\s]*employees',
        r'([\d,\.]+)[\+\s]*workers',
        r'([\d,\.]+)[\+\s]*staff',
        r'team of\s*([\d,\.]+)',
        r'([\d,\.]+)\s*people',
        r'([\d,\.]+)k\+?\s*employees',
        r'employs\s*([\d,\.]+)',
        r'workforce of\s*([\d,\.]+)',
        r'company size[:\s]*([\d,\.]+)',
        r'([\d,\.]+)\s*total employees',
        r'([\d,\.]+)\s*professionals',
        r'approximately\s*([\d,\.]+)\s*employees',
        r'about\s*([\d,\.]+)\s*employees',
        r'over\s*([\d,\.]+)\s*employees',
        r'more than\s*([\d,\.]+)\s*employees',
        r'([\d,\.]+)\s*employees worldwide',
        r'global workforce of\s*([\d,\.]+)',
        r'team size[:\s]*([\d,\.]+)',
        r'number of employees[:\s]*([\d,\.]+)',
        r'employee count[:\s]*([\d,\.]+)'
    ]
    
    for pattern in employee_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count_str = match.group(1).replace(',', '')
            try:
                if 'k' in count_str.lower():
                    return int(float(count_str.lower().replace('k', '')) * 1000)
                return int(float(count_str))
            except ValueError:
                continue
    return None

def check_company_website(company_name, session):
    """Try to find employee count on company website."""
    try:
        # Try to find company website via Google
        query = f"{company_name} singapore official website"
        search_url = f"https://www.google.com/search?q={quote(query)}"
        response = session.get(search_url, timeout=(5, 15))
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find first organic result (usually official website)
            for cite in soup.select('.iUh30'):
                if cite and not any(x in cite.text for x in ['linkedin', 'facebook', 'twitter', 'instagram']):
                    company_url = cite.text
                    print(f"Found company website: {company_url}")
                    
                    try:
                        # Check common about/company pages
                        paths = ['', '/about', '/about-us', '/company', '/about-company', '/careers']
                        for path in paths:
                            url = f"https://{company_url.strip('/')}{path}"
                            print(f"Checking URL: {url}")
                            
                            response = session.get(url, timeout=(5, 15))
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.text, 'html.parser')
                                text = soup.get_text().lower()
                                
                                count = find_employee_count(text)
                                if count:
                                    is_sg = 'singapore' in text or ' sg ' in text
                                    return {
                                        'count': count,
                                        'source': 'Company Website',
                                        'url': url,
                                        'is_sg': is_sg
                                    }
                    except Exception as e:
                        print(f"Error checking company website: {str(e)}")
                        continue
                    
                    break
    except Exception as e:
        print(f"Error finding company website: {str(e)}")
    return None

def extract_from_linkedin(company_name, session):
    """Try to find employee count on LinkedIn."""
    try:
        variations = [
            company_name.lower(),
            company_name.lower().replace(' ', '-'),
            f"{company_name.lower()}-singapore",
            company_name.lower().replace('pte', '').replace('ltd', '').strip()
        ]
        
        for slug in variations:
            url = f"https://www.linkedin.com/company/{slug}"
            print(f"Checking LinkedIn: {url}")
            
            try:
                response = session.get(url, timeout=(5, 15))
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text().lower()
                    
                    count = find_employee_count(text)
                    if count:
                        is_sg = 'singapore' in text or ' sg ' in text
                        return {
                            'count': count,
                            'source': 'LinkedIn',
                            'url': url,
                            'is_sg': is_sg
                        }
            except Exception as e:
                print(f"LinkedIn error for {slug}: {str(e)}")
            
            time.sleep(1)
    except Exception as e:
        print(f"LinkedIn general error: {str(e)}")
    return None

def extract_from_google(company_name, session):
    """Try to find employee count via Google search."""
    try:
        queries = [
            f"{company_name} singapore number of employees",
            f"{company_name} singapore company size",
            f"{company_name} singapore total employees",
            f"{company_name} singapore employee count linkedin",
            f"{company_name} singapore how many employees",
            f"{company_name} singapore workforce size"
        ]
        
        for query in queries:
            try:
                url = f"https://www.google.com/search?q={quote(query)}"
                print(f"Trying Google: {query}")
                
                response = session.get(url, timeout=(5, 15))
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Get text from search result snippets
                    snippets = []
                    for div in soup.select('.VwiC3b, .IsZvec, .MUxGbd'):
                        if div.string:
                            snippets.append(div.string.lower())
                    
                    text = ' '.join(snippets)
                    count = find_employee_count(text)
                    
                    if count:
                        is_sg = 'singapore' in text or ' sg ' in text
                        return {
                            'count': count,
                            'source': 'Google',
                            'url': url,
                            'is_sg': is_sg
                        }
            except Exception as e:
                print(f"Google error for query '{query}': {str(e)}")
            
            time.sleep(1)
    except Exception as e:
        print(f"Google general error: {str(e)}")
    return None

def extract_employee_count(company_name):
    """Main function to extract employee count from multiple sources."""
    print(f"\nSearching for employee count: {company_name}")
    session = get_session()
    
    # Try LinkedIn first
    result = extract_from_linkedin(company_name, session)
    if result:
        print(f"Found on LinkedIn: {result}")
        return result
        
    time.sleep(1)
    
    # Try company website
    result = check_company_website(company_name, session)
    if result:
        print(f"Found on company website: {result}")
        return result
        
    time.sleep(1)
    
    # Try Google search
    result = extract_from_google(company_name, session)
    if result:
        print(f"Found via Google: {result}")
        return result
    
    print(f"No employee count found for {company_name}")
    return {
        'company': company_name,
        'employee_count': 'Not found',
        'is_sg': False,
        'source': 'None',
        'url': '#',
        'other_sources': []
    }

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/leaderboard')
def get_leaderboard():
    scores = load_leaderboard()
    # Sort by time, then moves
    scores.sort(key=lambda x: (x['time'], x['moves']))
    return jsonify(scores[:10])  # Return top 10 scores

@app.route('/save-score', methods=['POST'])
def save_score():
    score_data = request.json
    scores = load_leaderboard()
    scores.append({
        'name': score_data['name'],
        'time': score_data['time'],
        'moves': score_data['moves']
    })
    # Sort and keep top 100 scores
    scores.sort(key=lambda x: (x['time'], x['moves']))
    scores = scores[:100]
    save_leaderboard(scores)
    return jsonify({'success': True})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        print(f"Received search request with data: {data}")
        
        # Handle both single company and list of companies
        if 'company' in data:
            companies = [data['company']]
        else:
            companies = data.get('companies', [])
        
        if not companies:
            print("No companies provided in request")
            return jsonify([])
        
        print(f"Processing companies: {companies}")
        
        # Process companies concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_company = {
                executor.submit(extract_employee_count, company): company 
                for company in companies
            }
            
            results = []
            for future in as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    result = future.result()
                    print(f"Results for {company}: {result}")
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"Error processing company {company}: {str(e)}")
                    results.append({
                        'company': company,
                        'employee_count': 'Error',
                        'is_sg': False,
                        'source': 'Error',
                        'url': '#',
                        'other_sources': [],
                        'error': str(e)
                    })
                
                # Add random delay to avoid rate limiting
                time.sleep(random.uniform(0.5, 1.0))
        
        print(f"Final results: {results}")
        return jsonify(results)
        
    except Exception as e:
        print(f"Search endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    sys.setrecursionlimit(1000)  # Set a reasonable recursion limit
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
