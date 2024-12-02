# SG Company Scanner

A web application that helps you find employee count information for companies in Singapore. The application scrapes data from multiple sources including LinkedIn and company websites.

## Features

- Search for multiple companies simultaneously (up to 50)
- Auto-expanding search box with Shift+Enter shortcut
- Concurrent processing of company searches
- Modern dark theme interface
- Mobile-responsive design
- Region detection (Singapore vs Global employee count)

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5002
```

## Usage

1. Enter company names in the search box (one per line)
2. Press the Search button or use Shift+Enter
3. View results in the table below
4. Click "View Source" to see the original data source

## Technical Details

- Backend: Python Flask
- Frontend: HTML, CSS, JavaScript
- Web Scraping: BeautifulSoup4
- Concurrent Processing: ThreadPoolExecutor
- Rate Limiting: Random delays between requests

## Notes

- The application respects rate limits and uses random user agents
- Results may vary based on data availability
- Maximum 50 companies can be searched at once
- Employee counts may be global or Singapore-specific

## License

MIT License
