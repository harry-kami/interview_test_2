"""Bincom test - Questions 1, 2 and 3 with Flask + sqlite3.
Run:  python app.py   (builds bincom.db on first start, then open http://127.0.0.1:5000)
"""
import os
import sqlite3
from datetime import datetime
from flask import Flask, g, redirect, render_template_string, request, url_for

from load_db import build

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "bincom.db")
if not os.path.exists(DB_PATH):      # first start on a fresh host: build the database
    build()

app = Flask(__name__)
PARTIES = ["PDP", "DPP", "ACN", "PPA", "CDC", "JP", "ANPP", "LABO", "CPP"]

PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bincom Election Results</title>
<style>
  body{font-family:system-ui,sans-serif;background:#f4f6f8;color:#222;margin:0}
  header{background:#1f3a5f;padding:14px 24px}
  header a{color:#cfe0f5;text-decoration:none;margin-right:22px;font-weight:500}
  header a.on{color:#fff;border-bottom:2px solid #fff;padding-bottom:3px}
  main{max-width:680px;margin:28px auto;background:#fff;padding:24px 28px;border-radius:8px;
       box-shadow:0 1px 4px rgba(0,0,0,.1)}
  h2{margin-top:0}
  label{display:block;margin:14px 0 4px;font-weight:600;font-size:.9rem}
  select,input{width:100%;padding:8px;border:1px solid #bbb;border-radius:5px;font-size:1rem;box-sizing:border-box}
  button{margin-top:18px;background:#1f3a5f;color:#fff;border:0;padding:10px 20px;border-radius:5px;
         font-size:1rem;cursor:pointer}
  button:hover{background:#2c5282}
  table{width:100%;border-collapse:collapse;margin-top:20px}
  th,td{padding:8px 12px;border-bottom:1px solid #e3e3e3;text-align:left}
  th{background:#eef2f7} td.n,th.n{text-align:right}
  tr.lead td{background:#e6f4ea;font-weight:600}
  tr.sum td{border-top:2px solid #1f3a5f;font-weight:700}
  .err{background:#fdecea;color:#b3261e;padding:10px;border-radius:5px}
  .note{color:#666;font-size:.9rem}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
</style>
<header>
  <a href="/" class="{{ 'on' if tab=='1' }}">Polling unit</a>
  <a href="/lga" class="{{ 'on' if tab=='2' }}">LGA total</a>
  <a href="/new" class="{{ 'on' if tab=='3' }}">Add result</a>
</header>
<main>BODY</main>
"""


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def page(body, **ctx):
    return render_template_string(PAGE.replace("BODY", body), **ctx)


# Reusable result table: highlights the leading party and adds a total row.
TABLE = """
{% macro results_table(rows, extra=None) %}
  <table>
    <tr><th>Party</th><th class="n">Score</th>{% if extra %}<th class="n">{{ extra }}</th>{% endif %}</tr>
    {% for r in rows %}
      <tr class="{{ 'lead' if loop.first }}"><td>{{ r.party }}</td><td class="n">{{ '{:,}'.format(r.score) }}</td>
      {% if extra %}<td class="n">{{ '{:,}'.format(r.other) if r.other is not none else '-' }}</td>{% endif %}</tr>
    {% endfor %}
    <tr class="sum"><td>Total votes</td><td class="n">{{ '{:,}'.format(rows|sum(attribute='score')) }}</td>
      {% if extra %}<td class="n">{{ '{:,}'.format(rows|sum(attribute='other')) }}</td>{% endif %}</tr>
  </table>
{% endmacro %}
"""


# ---------- Question 1: result for one polling unit ----------
@app.route("/")
def polling_unit():
    conn = db()
    # only LGAs / units that actually have results, so no dead-end choices
    lgas = conn.execute(
        """SELECT DISTINCT l.lga_id, l.lga_name FROM announced_pu_results a
           JOIN polling_unit p ON p.uniqueid = CAST(a.polling_unit_uniqueid AS INTEGER)
           JOIN lga l ON l.lga_id = p.lga_id ORDER BY l.lga_name""").fetchall()
    lga, pu = request.args.get("lga"), request.args.get("pu")
    units = []
    if lga:
        units = conn.execute(
            """SELECT p.uniqueid, p.polling_unit_name FROM polling_unit p
               WHERE p.lga_id = ? AND CAST(p.uniqueid AS TEXT) IN
                     (SELECT polling_unit_uniqueid FROM announced_pu_results)
               ORDER BY p.uniqueid""", (lga,)).fetchall()
    rows, unit = [], None
    if pu:
        unit = conn.execute("SELECT polling_unit_name FROM polling_unit WHERE uniqueid = ?", (pu,)).fetchone()
        rows = conn.execute(
            """SELECT party_abbreviation AS party, party_score AS score FROM announced_pu_results
               WHERE polling_unit_uniqueid = ? ORDER BY party_score DESC""", (pu,)).fetchall()
    return page(TABLE + """
    <h2>Polling unit result</h2>
    <form method="get">
      <label>1. Local government</label>
      <select name="lga" onchange="this.form.pu.value='';this.form.submit()">
        <option value="">Select an LGA...</option>
        {% for l in lgas %}<option value="{{ l.lga_id }}" {{ 'selected' if lga|string==l.lga_id|string }}>{{ l.lga_name }}</option>{% endfor %}
      </select>
      {% if lga %}
      <label>2. Polling unit</label>
      <select name="pu" onchange="this.form.submit()">
        <option value="">Select a polling unit...</option>
        {% for u in units %}<option value="{{ u.uniqueid }}" {{ 'selected' if pu|string==u.uniqueid|string }}>
          #{{ u.uniqueid }} - {{ u.polling_unit_name }}</option>{% endfor %}
      </select>
      {% endif %}
      <noscript><button>Show</button></noscript>
    </form>
    {% if unit %}<h3>{{ unit.polling_unit_name }} (#{{ pu }})</h3>{{ results_table(rows) }}
    {% elif pu %}<p class="note">No polling unit with that ID.</p>{% endif %}
    """, tab="1", lgas=lgas, lga=lga, units=units, pu=pu, unit=unit, rows=rows)


# ---------- Question 2: summed result per LGA (from polling units, NOT announced_lga_results) ----------
@app.route("/lga")
def lga_total():
    conn = db()
    lgas = conn.execute(
        """SELECT l.lga_id, l.lga_name, COUNT(DISTINCT p.uniqueid) AS units FROM lga l
           JOIN polling_unit p ON p.lga_id = l.lga_id
           JOIN announced_pu_results a ON CAST(a.polling_unit_uniqueid AS INTEGER) = p.uniqueid
           GROUP BY l.lga_id ORDER BY l.lga_name""").fetchall()
    total_lgas = conn.execute("SELECT COUNT(*) FROM lga").fetchone()[0]
    chosen = request.args.get("lga")
    rows, name, units = [], None, 0
    if chosen:
        row = next((l for l in lgas if str(l["lga_id"]) == chosen), None)
        if row:
            name, units = row["lga_name"], row["units"]
            # polling-unit sum is the answer; announced LGA figure is only a side-by-side comparison
            rows = conn.execute(
                """SELECT a.party_abbreviation AS party, SUM(a.party_score) AS score,
                          (SELECT party_score FROM announced_lga_results
                           WHERE lga_name = ? AND party_abbreviation = a.party_abbreviation) AS other
                   FROM announced_pu_results a
                   JOIN polling_unit p ON p.uniqueid = CAST(a.polling_unit_uniqueid AS INTEGER)
                   WHERE p.lga_id = ? GROUP BY a.party_abbreviation ORDER BY score DESC""",
                (chosen, chosen)).fetchall()
    return page(TABLE + """
    <h2>Total result by LGA</h2>
    <form method="get">
      <label>Local government</label>
      <select name="lga" onchange="this.form.submit()">
        <option value="">Select an LGA...</option>
        {% for l in lgas %}<option value="{{ l.lga_id }}" {{ 'selected' if chosen==l.lga_id|string }}>{{ l.lga_name }}</option>{% endfor %}
      </select>
      <noscript><button>Show total</button></noscript>
    </form>
    <p class="note">Showing {{ lgas|length }} of {{ total_lgas }} LGAs - the rest have no polling unit results in this database.</p>
    {% if name %}
      <h3>{{ name }} <span class="note">({{ units }} polling unit{{ 's' if units != 1 }} with results)</span></h3>
      {{ results_table(rows, 'Announced LGA figure') }}
    {% endif %}
    """, tab="2", lgas=lgas, total_lgas=total_lgas, chosen=chosen, rows=rows, name=name, units=units)


# ---------- Question 3: store results for a new polling unit ----------
@app.route("/new", methods=["GET", "POST"])
def new_result():
    conn = db()
    lgas = conn.execute("SELECT lga_id, lga_name FROM lga ORDER BY lga_name").fetchall()
    form = request.form if request.method == "POST" else {}
    lga = form.get("lga_id") or request.args.get("lga") or ""
    wards = conn.execute("SELECT uniqueid, ward_name FROM ward WHERE lga_id = ? ORDER BY ward_name",
                         (lga,)).fetchall() if lga else []
    errors = []
    if request.method == "POST":
        name, user = form.get("name", "").strip(), form.get("user", "").strip() or "anonymous"
        if not name: errors.append("Polling unit name is required.")
        if not lga: errors.append("Choose an LGA.")
        for p in PARTIES:
            v = form.get(p, "").strip()
            if not v.isdigit(): errors.append(f"{p}: enter a whole number (0 or more).")
        if not errors:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ward = conn.execute("SELECT ward_id, uniqueid FROM ward WHERE uniqueid = ?",
                                (form.get("ward") or 0,)).fetchone()
            ward_id, ward_uid = (ward["ward_id"], ward["uniqueid"]) if ward else (0, None)
            cur = conn.execute(
                "INSERT INTO polling_unit (polling_unit_id, ward_id, uniquewardid, lga_id, polling_unit_name, "
                "entered_by_user, date_entered, user_ip_address) VALUES (0, ?, ?, ?, ?, ?, ?, ?)",
                (ward_id, ward_uid, int(lga), name, user, now, request.remote_addr))
            pu_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO announced_pu_results (polling_unit_uniqueid, party_abbreviation, party_score, "
                "entered_by_user, date_entered, user_ip_address) VALUES (?,?,?,?,?,?)",
                [(str(pu_id), p, int(form[p]), user, now, request.remote_addr) for p in PARTIES])
            conn.commit()
            return redirect(url_for("polling_unit", lga=lga, pu=pu_id))
    return page("""
    <h2>Add results for a new polling unit</h2>
    {% if errors %}<div class="err">{% for e in errors %}{{ e }}<br>{% endfor %}</div>{% endif %}
    <form method="post">
      <label>Local government</label>
      <select name="lga_id" onchange="location='/new?lga='+this.value">
        <option value="">Select an LGA...</option>
        {% for l in lgas %}<option value="{{ l.lga_id }}" {{ 'selected' if lga|string==l.lga_id|string }}>{{ l.lga_name }}</option>{% endfor %}
      </select>
      <label>Ward <span class="note">(optional - pick an LGA first)</span></label>
      <select name="ward"><option value="">-</option>
        {% for w in wards %}<option value="{{ w.uniqueid }}" {{ 'selected' if form.get('ward')==w.uniqueid|string }}>{{ w.ward_name }}</option>{% endfor %}
      </select>
      <label>Polling unit name</label><input name="name" value="{{ form.get('name','') }}" required>
      <label>Entered by</label><input name="user" value="{{ form.get('user','') }}">
      <h3>Party scores</h3>
      <div class="grid">
      {% for p in parties %}<div><label>{{ p }}</label>
        <input name="{{ p }}" type="number" min="0" value="{{ form.get(p,'') }}" required></div>{% endfor %}
      </div>
      <button>Save result</button>
    </form>""", tab="3", lgas=lgas, lga=lga, wards=wards, form=form, errors=errors, parties=PARTIES)


if __name__ == "__main__":
    app.run()
