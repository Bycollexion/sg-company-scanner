from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup
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
        thread_local.session = requests.Session()
        thread_local.session.headers.update({
            'User-Agent': UserAgent().random
        })
    return thread_local.session

def extract_from_linkedin(company_name, session):
    try:
        search_url = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}"
        response = session.get(search_url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            text_content = soup.get_text().lower()
            
            employee_patterns = [
                r'([\d,]+)\s*employees',
                r'([\d,]+)\s*workers',
                r'([\d,]+)\s*staff',
                r'team of\s*([\d,]+)',
            ]
            
            for pattern in employee_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    count = int(match.group(1).replace(',', ''))
                    return {
                        'count': count,
                        'source': 'LinkedIn',
                        'url': search_url,
                        'is_sg': 'Singapore' in response.text or 'SG' in response.text
                    }
    except Exception as e:
        print(f"LinkedIn error for {company_name}: {str(e)}")
    return None

def extract_from_google(company_name, session):
    try:
        search_url = f"https://www.google.com/search?q={company_name}+singapore+number+of+employees+site:linkedin.com+OR+site:glassdoor.com+OR+site:jobstreet.com.sg"
        response = session.get(search_url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            text_content = soup.get_text().lower()
            
            employee_patterns = [
                r'([\d,]+)\s*employees',
                r'([\d,]+)\s*workers',
                r'([\d,]+)\s*staff',
                r'team of\s*([\d,]+)',
            ]
            
            for pattern in employee_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    count = int(match.group(1).replace(',', ''))
                    return {
                        'count': count,
                        'source': 'Google Search',
                        'url': search_url,
                        'is_sg': True  # Since we specifically searched for Singapore
                    }
    except Exception as e:
        print(f"Google error for {company_name}: {str(e)}")
    return None

def extract_from_jobstreet(company_name, session):
    try:
        search_url = f"https://www.jobstreet.com.sg/en/companies/{company_name.lower().replace(' ', '-')}"
        response = session.get(search_url, timeout=10)
        
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
        response = session.get(search_url, timeout=10)
        
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
    try:
        session = get_session()
        sources = []
        
        # Try all sources
        linkedin_data = extract_from_linkedin(company_name, session)
        if linkedin_data:
            sources.append(linkedin_data)
        
        time.sleep(random.uniform(1, 2))  # Random delay between requests
        
        google_data = extract_from_google(company_name, session)
        if google_data:
            sources.append(google_data)
        
        time.sleep(random.uniform(1, 2))
        
        jobstreet_data = extract_from_jobstreet(company_name, session)
        if jobstreet_data:
            sources.append(jobstreet_data)
        
        time.sleep(random.uniform(1, 2))
        
        glassdoor_data = extract_from_glassdoor(company_name, session)
        if glassdoor_data:
            sources.append(glassdoor_data)
        
        if sources:
            # Sort sources by count to identify outliers
            sources.sort(key=lambda x: x['count'])
            
            # If we have multiple sources, try to identify the most reliable count
            if len(sources) > 1:
                # If counts are similar (within 20% difference), use the median
                counts = [s['count'] for s in sources]
                median_count = counts[len(counts)//2]
                
                # Filter sources with counts within 20% of median
                reliable_sources = [s for s in sources if abs(s['count'] - median_count) / median_count <= 0.2]
                
                if reliable_sources:
                    sources = reliable_sources
            
            # Prioritize Singapore-specific data
            sg_sources = [s for s in sources if s['is_sg']]
            if sg_sources:
                sources = sg_sources
            
            # Return the most reliable source (preferring LinkedIn and Singapore-specific data)
            best_source = sources[0]
            if len(sources) > 1:
                for source in sources:
                    if source['source'] == 'LinkedIn' and source['is_sg']:
                        best_source = source
                        break
            
            return {
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
    data = request.get_json()
    companies = data.get('companies', [])
    
    if not companies:
        return jsonify([])
    
    # Limit to 50 companies at a time
    companies = companies[:50]
    
    # Process companies concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_company = {
            executor.submit(extract_employee_count, company): company 
            for company in companies
        }
        
        results = []
        for future in as_completed(future_to_company):
            result = future.result()
            if result:
                results.append(result)
            
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(0.5, 1.5))
    
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
