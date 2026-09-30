# Strava Fitness Analytics — Streamlit + SQL

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Pages
1. **Dashboard** — KPIs, weekday steps, activity intensity, daily trends, hourly calorie pattern.
2. **SQL Analysis** — ready-made SQL analyses plus a custom SELECT/WITH SQL runner.
3. **Data Quality** — source/coverage notes and table row counts.

The app loads the supplied Fitbit fitness CSVs into SQLite automatically on startup.
