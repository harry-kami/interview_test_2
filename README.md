# Bincom election results (Flask + SQLite)
- `/`     Q1: result for one polling unit
- `/lga`  Q2: summed polling-unit result per LGA
- `/new`  Q3: store results for a new polling unit

Run locally: `pip install -r requirements.txt` then `python app.py`.
The SQLite database is built automatically from `bincom_test.sql` on first start.
Start command on hosts such as Render: `gunicorn app:app`.
