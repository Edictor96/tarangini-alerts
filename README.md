# Taranगिनी — Disaster Management Demo

Taranगिनी is a coastal disaster alert system that scrapes real-time alerts from INCOIS (Indian National Centre for Ocean Information Services) and displays them on an interactive web interface.

## 🏗️ Architecture & Data Flow

```
┌─────────────────┐
│ INCOIS Website  │
│ (incois.gov.in) │
└────────┬────────┘
         │
         │ Scrapes alerts
         ▼
┌─────────────────────┐
│ incois_scraper.py   │
│ (Python Script)     │
└─────────┬───────────┘
          │
          │ Saves to
          ▼
┌─────────────────────┐
│   alerts.json       │
│   (Data Storage)    │
└─────────┬───────────┘
          │
          │ Loaded by
          ▼
┌─────────────────────┐
│   main.py           │
│   (FastAPI Backend) │
│   - /alerts API     │
│   - /refresh-alerts │
└─────────┬───────────┘
          │
          │ Serves data via API
          ▼
┌─────────────────────┐
│   index.html        │
│   (Frontend UI)     │
│   - Displays alerts │
│   - Refresh button  │
└─────────────────────┘
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Scraper (Optional - generates sample data if offline)
```bash
python incois_scraper.py
```
This creates/updates `alerts.json` with the latest alerts from INCOIS.

### 3. Start the Web Server
```bash
python -m uvicorn main:app --reload
```

### 4. Open in Browser
Navigate to: **http://127.0.0.1:8000**

## 📡 API Endpoints

- **`GET /`** - Main web interface (frontend)
- **`GET /alerts`** - JSON API returning all alerts
- **`GET /refresh-alerts`** - Runs the scraper and refreshes alerts
- **`GET /reload`** - Reloads alerts from alerts.json
- **`GET /db-view`** - Database viewer interface
- **`GET /alerts-nearby?lat=X&lng=Y&radius_km=Z`** - Get alerts near a location

## 🔄 How to Update Alerts

### Method 1: From the Web UI
Click the **"🔄 Refresh Alerts"** button on the homepage. This will:
1. Run the scraper in the background
2. Fetch latest alerts from INCOIS
3. Update the database
4. Refresh the display automatically

### Method 2: Manual Scraper Run
```bash
python incois_scraper.py
```
The backend automatically reloads `alerts.json` on each page load.

### Method 3: Via API
```bash
curl http://localhost:8000/refresh-alerts
```

## 📁 Project Structure

```
tarangini-alerts/
├── main.py                 # FastAPI backend server
├── incois_scraper.py       # INCOIS website scraper
├── alerts.json             # Scraped alerts data (auto-generated)
├── requirements.txt        # Python dependencies
├── templates/
│   ├── index.html          # Main frontend UI
│   └── db_view.html        # Database viewer
├── static/
│   └── logo.jpg            # Application logo
└── README.md               # This file
```

## 🛠️ Technologies Used

- **Backend**: FastAPI, SQLModel, SQLite
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Scraper**: BeautifulSoup4, Requests, Geopy, Feedparser
- **Deployment**: Uvicorn (ASGI server)

## 📊 Database Schema

The `Alert` model stores:
- `id` - Unique identifier
- `source` - Alert source (e.g., "INCOIS")
- `severity` - emergency, warning, info, or caution
- `title` - Alert headline
- `message` - Detailed alert message
- `time` - Timestamp when alert was recorded
- `lat`, `lng` - Geographic coordinates (optional)

## 🔍 Features

✅ Real-time alert scraping from INCOIS  
✅ Interactive web interface with alert cards  
✅ One-click refresh from UI  
✅ Severity-based color coding  
✅ Location-based filtering via API  
✅ Responsive mobile-friendly design  
✅ Automatic fallback to sample data when offline  

## 📝 Notes

- The scraper generates sample alerts when INCOIS website is unreachable
- Alerts are automatically loaded from `alerts.json` on each page load
- The database (SQLite) is used as an intermediate layer for querying and filtering

## 🤝 Contributing

Feel free to open issues or submit pull requests to improve the system!

## 📄 License

This project is for educational and demonstration purposes.
