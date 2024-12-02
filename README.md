# Singapore Company Scanner

A web application that retrieves employee count information for companies in Singapore from multiple online sources.

## Features

- Search for multiple companies simultaneously (up to 50)
- Cross-references data from multiple sources:
  - LinkedIn
  - Google Search
- Displays employee count, location, and source information
- Direct links to LinkedIn company profiles
- Modern, responsive UI
- Shift+Enter shortcut for quick searching

## Tech Stack

- Backend: Python Flask
- Frontend: HTML, CSS, JavaScript
- Web Scraping: BeautifulSoup4
- HTTP Requests: Python Requests
- User Agent Management: fake-useragent
- Production Server: Gunicorn with Gevent

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```

## Development

The application will run on `http://localhost:5002` by default.

## Production Deployment

This application is configured for deployment on Render. The `render.yaml` file contains all necessary deployment configurations.

## Environment Variables

No environment variables are required for basic functionality.

## Notes

- The application implements rate limiting and random delays to avoid being blocked
- User agents are randomized for each request
- Concurrent processing is limited to prevent overloading sources
