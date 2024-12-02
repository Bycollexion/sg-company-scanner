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

def extract_text_without_recursion(element):
    """Extract text from HTML elements without recursive calls."""
    if not element:
        return ""
        
    try:
        # Get direct text content
        text = element.string
        if text and text.strip():
            return text.strip()
            
        # Get text from immediate children
        texts = []
        for child in element.children:
            if isinstance(child, str) and child.strip():
                texts.append(child.strip())
            elif hasattr(child, 'string') and child.string and child.string.strip():
                texts.append(child.string.strip())
        
        return ' '.join(texts)
        
    except Exception as e:
        print(f"Error extracting text: {str(e)}")
        return ""

def extract_from_linkedin(company_name, session):
    try:
        # Try multiple variations of the company name
        company_variations = [
            company_name.lower(),
            company_name.lower().replace(' ', '-'),
            company_name.lower().replace(' ', ''),
            f"{company_name.lower()}-singapore",
            f"{company_name.lower().replace(' ', '-')}-sg",
            company_name.lower().replace('pte', '').replace('ltd', '').strip(),
            company_name.lower().replace('private', '').replace('limited', '').strip(),
            company_name.lower().replace('singapore', '').replace('sg', '').strip()
        ]
        
        # Remove duplicates and empty strings
        company_variations = list(set(filter(None, company_variations)))
        print(f"Trying LinkedIn variations for {company_name}: {company_variations}")
        
        for company_slug in company_variations:
            search_url = f"https://www.linkedin.com/company/{company_slug}"
            try:
                print(f"Trying LinkedIn URL: {search_url}")
                response = session.get(search_url, timeout=(5, 15))
                print(f"LinkedIn response for {company_name} ({company_slug}): {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer(['p', 'div', 'span']))
                    text_content = extract_text_without_recursion(soup).lower()
                    
                    # Enhanced patterns for employee count
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
                        r'([\d,\.]+)\s*professionals'
                    ]
                    
                    for pattern in employee_patterns:
                        match = re.search(pattern, text_content, re.IGNORECASE)
                        if match:
                            count_str = match.group(1).replace(',', '')
                            if 'k' in count_str.lower():
                                count = float(count_str.lower().replace('k', '')) * 1000
                            else:
                                count = float(count_str)
                            
                            is_sg = ('singapore' in text_content or 
                                   ' sg ' in text_content or 
                                   'singapore office' in text_content or 
                                   'singapore headquarters' in text_content)
                            
                            print(f"Found LinkedIn data for {company_name}: {count} employees, SG: {is_sg}")
                            
                            return {
                                'count': int(count),
                                'source': 'LinkedIn',
                                'url': search_url,
                                'is_sg': is_sg
                            }
                    
                    print(f"No employee count found in LinkedIn page for {company_name} ({company_slug})")
                
            except requests.exceptions.RequestException as e:
                print(f"LinkedIn request error for {company_name} at {search_url}: {str(e)}")
                continue
            except Exception as e:
                print(f"LinkedIn parsing error for {company_name} at {search_url}: {str(e)}")
                continue
            
            time.sleep(random.uniform(0.5, 1))
            
    except Exception as e:
        print(f"LinkedIn general error for {company_name}: {str(e)}")
    return None

def extract_from_google(company_name, session):
    try:
        search_queries = [
            f"{company_name} singapore employees site:linkedin.com",
            f"{company_name} singapore company size",
            f"{company_name} singapore workforce",
            f"{company_name} singapore staff strength",
            f"{company_name} singapore total employees",
            f"{company_name} singapore careers number of employees",
            f"{company_name} singapore about us employees"
        ]
        
        print(f"Trying Google search queries for {company_name}")
        
        for query in search_queries:
            try:
                encoded_query = quote(query)
                search_url = f"https://www.google.com/search?q={encoded_query}"
                print(f"Trying Google query: {query}")
                
                response = session.get(search_url, timeout=(5, 15))
                print(f"Google response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Use a simpler parsing approach
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Only get direct text from specific divs
                    snippets = []
                    
                    # Search result divs
                    for div in soup.select('div.VwiC3b'):
                        if div and div.string:
                            snippets.append(div.string.lower())
                    
                    # Description divs
                    for div in soup.select('div.IsZvec'):
                        if div and div.string:
                            snippets.append(div.string.lower())
                            
                    # Combine all text
                    text_content = ' '.join(snippets)
                    
                    # Enhanced patterns for employee count
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
                        r'([\d,\.]+)\s*professionals'
                    ]
                    
                    for pattern in employee_patterns:
                        match = re.search(pattern, text_content, re.IGNORECASE)
                        if match:
                            count_str = match.group(1).replace(',', '')
                            if 'k' in count_str.lower():
                                count = float(count_str.lower().replace('k', '')) * 1000
                            else:
                                count = float(count_str)
                            
                            # Check if the result is specific to Singapore
                            context = text_content[max(0, match.start() - 100):min(len(text_content), match.end() + 100)]
                            is_sg = ('singapore' in context or 
                                   ' sg ' in context or 
                                   'singapore office' in context or 
                                   'singapore headquarters' in context)
                            
                            print(f"Found Google data for {company_name}: {count} employees, SG: {is_sg}")
                            
                            return {
                                'count': int(count),
                                'source': 'Google',
                                'url': search_url,
                                'is_sg': is_sg
                            }
                    
                    print(f"No employee count found in Google results for query: {query}")
                
            except requests.exceptions.RequestException as e:
                print(f"Google request error for {company_name} with query '{query}': {str(e)}")
                continue
            except Exception as e:
                print(f"Google parsing error for {company_name} with query '{query}': {str(e)}")
                continue
            
            time.sleep(random.uniform(1, 2))
            
    except Exception as e:
        print(f"Google general error for {company_name}: {str(e)}")
    return None

def extract_from_jobstreet(company_name, session):
    try:
        search_url = f"https://www.jobstreet.com.sg/en/companies/{company_name.lower().replace(' ', '-')}"
        response = session.get(search_url, timeout=(5, 15))
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            text_content = soup.get_text().lower()
            
            employee_patterns = [
                r'([\d,]+)\s*employees',
                r'([\d,]+)\s*workers',
                r'company size:\s*([\d,]+)',
            ]
            
            for pattern in employee_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    count = int(match.group(1).replace(',', ''))
                    return {
                        'count': count,
                        'source': 'JobStreet',
                        'url': search_url,
                        'is_sg': True
                    }
    except Exception as e:
        print(f"JobStreet error for {company_name}: {str(e)}")
    return None

def extract_from_glassdoor(company_name, session):
    try:
        search_url = f"https://www.glassdoor.sg/Overview/Working-at-{company_name.lower().replace(' ', '-')}"
        response = session.get(search_url, timeout=(5, 15))
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            text_content = soup.get_text().lower()
            
            employee_patterns = [
                r'size:\s*([\d,]+)\s*employees',
                r'([\d,]+)\s*employees',
                r'company size:\s*([\d,]+)',
            ]
            
            for pattern in employee_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    count = int(match.group(1).replace(',', ''))
                    return {
                        'count': count,
                        'source': 'Glassdoor',
                        'url': search_url,
                        'is_sg': 'Singapore' in response.text or 'SG' in response.text
                    }
    except Exception as e:
        print(f"Glassdoor error for {company_name}: {str(e)}")
    return None

def extract_employee_count(company_name):
    print(f"\nStarting extraction for company: {company_name}")
    try:
        session = get_session()
        sources = []
        
        # Try LinkedIn first
        print(f"Trying LinkedIn for {company_name}")
        linkedin_data = extract_from_linkedin(company_name, session)
        if linkedin_data:
            sources.append(linkedin_data)
            print(f"LinkedIn data found: {linkedin_data}")
        else:
            print(f"No LinkedIn data found for {company_name}")
        
        time.sleep(random.uniform(1, 2))
        
        # Try Google next
        print(f"Trying Google for {company_name}")
        google_data = extract_from_google(company_name, session)
        if google_data:
            sources.append(google_data)
            print(f"Google data found: {google_data}")
        else:
            print(f"No Google data found for {company_name}")
        
        if sources:
            print(f"Found {len(sources)} sources for {company_name}")
            # Sort sources by count to identify outliers
            sources.sort(key=lambda x: x['count'])
            
            # If we have multiple sources, try to identify the most reliable count
            if len(sources) > 1:
                print(f"Multiple sources found for {company_name}, analyzing reliability")
                # If counts are similar (within 20% difference), use the median
                counts = [s['count'] for s in sources]
                median_count = counts[len(counts)//2]
                
                # Filter sources with counts within 20% of median
                reliable_sources = [s for s in sources if abs(s['count'] - median_count) / median_count <= 0.2]
                
                if reliable_sources:
                    sources = reliable_sources
                    print(f"Filtered to {len(reliable_sources)} reliable sources")
            
            # Prioritize Singapore-specific data
            sg_sources = [s for s in sources if s['is_sg']]
            if sg_sources:
                sources = sg_sources
                print(f"Found {len(sg_sources)} Singapore-specific sources")
            
            # Return the most reliable source
            best_source = sources[0]
            if len(sources) > 1:
                for source in sources:
                    if source['source'] == 'LinkedIn' and source['is_sg']:
                        best_source = source
                        break
            
            result = {
                'company': company_name,
                'employee_count': best_source['count'],
                'is_sg': best_source['is_sg'],
                'source': best_source['source'],
                'url': best_source['url'],
                'other_sources': [
                    {
                        'count': s['count'],
                        'source': s['source'],
                        'is_sg': s['is_sg']
                    } for s in sources if s != best_source
                ]
            }
            print(f"Final result for {company_name}: {result}")
            return result
        
        print(f"No sources found for {company_name}")
        return {
            'company': company_name,
            'employee_count': 'Not found',
            'is_sg': False,
            'source': 'None',
            'url': '#',
            'other_sources': []
        }
        
    except Exception as e:
        print(f"Error processing {company_name}: {str(e)}")
        return {
            'company': company_name,
            'employee_count': 'Error',
            'is_sg': False,
            'source': 'Error',
            'url': '#',
            'other_sources': [],
            'error': str(e)
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
