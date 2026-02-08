import os
import re
import time
import json
import requests
from flask import Flask, request, Response, make_response
from bs4 import BeautifulSoup

app = Flask(__name__)

# -------------------------
# Config
# -------------------------
TARGET_BASE = os.getenv("TARGET_BASE", "https://pakistandatabase.com")
TARGET_PATH = os.getenv("TARGET_PATH", "/databases/sim.php")
ALLOW_UPSTREAM = True
MIN_INTERVAL = float(os.getenv("MIN_INTERVAL", "1.0"))
LAST_CALL = {"ts": 0.0}

# Developer
DEVELOPER = "Haseeb Sahil"

# -------------------------
# CORS Headers
# -------------------------
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.after_request
def after_request(response):
    return add_cors_headers(response)

# -------------------------
# Helpers
# -------------------------
def is_mobile(value: str) -> bool:
    return bool(re.fullmatch(r"92\d{10}", value))

def is_local_mobile(value: str) -> bool:
    return bool(re.fullmatch(r"03\d{9}", value))

def is_cnic(value: str) -> bool:
    return bool(re.fullmatch(r"\d{13}", value))

def normalize_mobile(value: str) -> str:
    value = value.strip()
    if is_mobile(value):
        return value
    if is_local_mobile(value):
        return "92" + value[1:]
    return value

def classify_query(value: str):
    v = value.strip()
    if is_cnic(v):
        return "cnic", v

    normalized = normalize_mobile(v)
    if is_mobile(normalized):
        return "mobile", normalized

    raise ValueError(
        "Invalid query. Use CNIC (13 digits) or mobile (03XXXXXXXXX / 92XXXXXXXXXX)."
    )

def rate_limit_wait():
    now = time.time()
    elapsed = now - LAST_CALL["ts"]
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    LAST_CALL["ts"] = time.time()

def fetch_upstream(query_value: str):
    if not ALLOW_UPSTREAM:
        raise PermissionError("Upstream fetching disabled.")

    rate_limit_wait()

    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "Referer": TARGET_BASE.rstrip("/") + "/",
        "Accept-Language": "en-US,en;q=0.9",
    }

    url = TARGET_BASE.rstrip("/") + TARGET_PATH
    data = {"search_query": query_value}

    resp = session.post(url, headers=headers, data=data, timeout=20)
    resp.raise_for_status()
    return resp.text

# -------------------------
# FIXED: Parse table with improved logic
# -------------------------
def parse_table(html: str):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "api-response"}) or soup.find("table")
    if not table:
        return []

    tbody = table.find("tbody")
    if not tbody:
        # If no tbody, try direct tr children
        rows = table.find_all("tr")
        if len(rows) <= 1:  # Only header row
            return []
        rows = rows[1:]  # Skip header
    else:
        rows = tbody.find_all("tr")

    results = []
    seen = set()

    for tr in rows:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cols) < 3:
            continue
            
        mobile = cols[0] if len(cols) > 0 else "N/A"
        name = cols[1] if len(cols) > 1 else "N/A"
        cnic = cols[2] if len(cols) > 2 else "N/A"
        address = cols[3] if len(cols) > 3 else "N/A"

        # Clean up mobile number
        if mobile == "N/A" or not mobile:
            continue
            
        # Extract only digits from mobile
        mobile_digits = re.sub(r'\D', '', mobile)
        if not mobile_digits:
            continue
            
        # Format mobile number
        if mobile_digits.startswith('92'):
            mobile_formatted = mobile_digits
        elif mobile_digits.startswith('3') and len(mobile_digits) == 10:
            mobile_formatted = '92' + mobile_digits
        elif len(mobile_digits) == 11 and mobile_digits.startswith('03'):
            mobile_formatted = '92' + mobile_digits[1:]
        else:
            mobile_formatted = mobile_digits

        # Use a tuple key to remove duplicates (mobile+cnic)
        key = (mobile_formatted, cnic)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "mobile": mobile_formatted,
            "name": name if name and name != "N/A" else "N/A",
            "cnic": cnic if cnic and cnic != "N/A" else "N/A",
            "address": address if address and address != "N/A" else "N/A"
        })

    return results

def make_response_object(query, qtype, results):
    return {
        "query": query,
        "query_type": qtype,
        "results_count": len(results),
        "results": results,
        "developer": DEVELOPER
    }

def respond_json(obj, pretty=False, status=200):
    text = json.dumps(obj, indent=2 if pretty else None, ensure_ascii=False)
    response = Response(text, mimetype="application/json; charset=utf-8", status=status)
    return add_cors_headers(response)

# -------------------------
# Routes
# -------------------------
@app.route("/", methods=["GET"])
def home():
    response = make_response(f"""
<!DOCTYPE html>
<html>
<head>
    <title>HS Pakistan SIM & CNIC Intelligence API</title>
    <style>
        body {{
            background: #0b0f19;
            color: #e5e7eb;
            font-family: Arial, Helvetica, sans-serif;
            padding: 30px;
        }}
        .box {{
            max-width: 820px;
            margin: auto;
            background: #111827;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 0 25px rgba(0,0,0,0.6);
        }}
        h1 {{ color: #38bdf8; }}
        h3 {{ color: #a5b4fc; }}
        .status {{ color: #22c55e; font-weight: bold; }}
        .dev {{ color: #facc15; }}
        ul {{ line-height: 1.9; }}
        code {{
            background: #020617;
            padding: 5px 8px;
            border-radius: 6px;
            color: #38bdf8;
        }}
        a {{ color: #38bdf8; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="box">
        <h1>🔍 HS Pakistan SIM & CNIC Intelligence API</h1>
        <p>⚡ <b>Live Lookup Engine</b></p>

        <p>
            🟢 Status: <span class="status">LIVE</span><br>
            👑 Developer: <span class="dev">{DEVELOPER}</span>
        </p>

        <h3>🚀 Features</h3>
        <ul>
            <li>Accepts 03XXXXXXXXX & 92XXXXXXXXXX</li>
            <li>CNIC Lookup Supported</li>
            <li>JSON API Response</li>
            <li>High-Speed Live Fetch</li>
            <li>CORS Enabled</li>
        </ul>

        <h3>🧪 Endpoints</h3>
        <ul>
            <li>
                GET <code>/api/lookup?query=03XXXXXXXXX</code><br>
                Example: <code>https://your-api.vercel.app/api/lookup?query=03001234567</code>
            </li>
            <li>
                POST <code>/api/lookup</code><br>
                JSON: <code>{{"query":"03xx"}}</code>
            </li>
        </ul>
        
        <h3>📡 Usage in JavaScript</h3>
        <code>
        fetch('https://your-api.vercel.app/api/lookup?query=03001234567')<br>
          .then(res => res.json())<br>
          .then(data => console.log(data))
        </code>
    </div>
</body>
</html>
""")
    return add_cors_headers(response)

@app.route("/api/lookup", methods=["GET", "OPTIONS"])
def api_lookup_get():
    if request.method == "OPTIONS":
        return add_cors_headers(Response())
        
    q = request.args.get("query") or request.args.get("q") or request.args.get("value")
    pretty = request.args.get("pretty") in ("1", "true", "True")

    if not q:
        return respond_json({"error": "Use ?query=<mobile or cnic>", "developer": DEVELOPER}, pretty, 400)

    try:
        qtype, normalized = classify_query(q)
        html = fetch_upstream(normalized)
        results = parse_table(html)
        return respond_json(make_response_object(normalized, qtype, results), pretty)
    except ValueError as e:
        return respond_json({"error": str(e), "developer": DEVELOPER}, pretty, 400)
    except Exception as e:
        return respond_json({"error": "Fetch failed", "detail": str(e), "developer": DEVELOPER}, pretty, 500)

@app.route("/api/lookup/<path:q>", methods=["GET", "OPTIONS"])
def api_lookup_path(q):
    if request.method == "OPTIONS":
        return add_cors_headers(Response())
        
    pretty = request.args.get("pretty") in ("1", "true", "True")
    try:
        qtype, normalized = classify_query(q)
        html = fetch_upstream(normalized)
        results = parse_table(html)
        return respond_json(make_response_object(normalized, qtype, results), pretty)
    except ValueError as e:
        return respond_json({"error": str(e), "developer": DEVELOPER}, pretty, 400)
    except Exception as e:
        return respond_json({"error": "Fetch failed", "detail": str(e), "developer": DEVELOPER}, pretty, 500)

@app.route("/api/lookup", methods=["POST", "OPTIONS"])
def api_lookup_post():
    if request.method == "OPTIONS":
        return add_cors_headers(Response())
        
    pretty = request.args.get("pretty") in ("1", "true", "True")
    data = request.get_json(force=True, silent=True) or {}
    q = data.get("query") or data.get("number") or data.get("value")

    if not q:
        return respond_json({"error": "Send JSON {\"query\":\"...\"}", "developer": DEVELOPER}, pretty, 400)

    try:
        qtype, normalized = classify_query(q)
        html = fetch_upstream(normalized)
        results = parse_table(html)
        return respond_json(make_response_object(normalized, qtype, results), pretty)
    except ValueError as e:
        return respond_json({"error": str(e), "developer": DEVELOPER}, pretty, 400)
    except Exception as e:
        return respond_json({"error": "Fetch failed", "detail": str(e), "developer": DEVELOPER}, pretty, 500)

@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return add_cors_headers(Response())
    return respond_json({"status": "ok", "developer": DEVELOPER})

# -------------------------
# Error Handlers
# -------------------------
@app.errorhandler(404)
def not_found(e):
    return respond_json({"error": "Not Found", "developer": DEVELOPER}, status=404)

@app.errorhandler(500)
def server_error(e):
    return respond_json({"error": "Internal Server Error", "developer": DEVELOPER}, status=500)

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)