#!/usr/bin/env python3

from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from datetime import datetime, timezone, timedelta

import hashlib
import json
import os
import secrets
import sqlite3
import sys


# ==========================
# PATH
# ==========================

ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT))

from ai.pdf_reader import extract_pdf_text
from ai.analyzer import analyze_report


DB_PATH = ROOT / "data" / "dipac.db"

UPLOAD_DIR = ROOT / "uploads"

REPORT_DIR = ROOT / "reports"


PORT = 8000

MAX_REPORT_SIZE = 20 * 1024 * 1024



# ==========================
# DATABASE
# ==========================

def db():

    connection = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    return connection



def password_hash(password):

    salt = secrets.token_hex(16)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200_000
    ).hex()

    return f"{salt}${derived}"



def init_db():

    DB_PATH.parent.mkdir(
        exist_ok=True
    )

    UPLOAD_DIR.mkdir(
        exist_ok=True
    )

    REPORT_DIR.mkdir(
        exist_ok=True
    )


    with db() as con:


        con.executescript("""

        CREATE TABLE IF NOT EXISTS users(

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            created_at TEXT

        );


        CREATE TABLE IF NOT EXISTS events(

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            event_date TEXT,
            location TEXT,
            category TEXT

        );


        CREATE TABLE IF NOT EXISTS event_metrics(

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER UNIQUE,
            total_revenue INTEGER DEFAULT 0,
            total_profit INTEGER DEFAULT 0,
            pax INTEGER DEFAULT 0,
            transactions INTEGER DEFAULT 0

        );


        CREATE TABLE IF NOT EXISTS ai_insights(

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            recommendation TEXT,
            created_at TEXT

        );


        CREATE TABLE IF NOT EXISTS reports(

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            file_name TEXT,
            event_name TEXT,
            event_date TEXT,
            location TEXT,
            pax INTEGER,
            revenue INTEGER,
            cost INTEGER,
            profit INTEGER,
            analysis TEXT,
            insights_json TEXT,
            created_at TEXT

        );


        CREATE TABLE IF NOT EXISTS transactions(

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            category TEXT,
            menu TEXT,
            qty INTEGER,
            customer_price INTEGER,
            customer_revenue INTEGER,
            collective_share INTEGER,
            commission_pct REAL,
            profit INTEGER

        );


        """)


        existing_columns = {
            row["name"]
            for row in con.execute("PRAGMA table_info(reports)")
        }

        if "insights_json" not in existing_columns:

            con.execute(
                "ALTER TABLE reports ADD COLUMN insights_json TEXT"
            )



        user = con.execute(
            "SELECT * FROM users"
        ).fetchone()



        if not user:

            admin_password = os.environ.get("DIPAC_ADMIN_PASSWORD")
            if not admin_password:
                admin_password = secrets.token_urlsafe(9)
                print(
                    f"[dipac] No DIPAC_ADMIN_PASSWORD set - generated admin "
                    f"password for admin@dipac.co: {admin_password}\n"
                    f"[dipac] Save this now, it will not be shown again. "
                    f"Change it later from the dashboard Account page."
                )

            con.execute(
            """
            INSERT INTO users
            VALUES(NULL,?,?,?,?,?)
            """,

            (

            "DIPAC Administrator",

            "admin@dipac.co",

            password_hash(
                admin_password
            ),

            "Administrator",

            datetime.now(
                timezone.utc
            ).isoformat()

            )

            )



        total = con.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]



        if total == 0:


            con.executemany(

            """
            INSERT INTO events
            VALUES(NULL,?,?,?,?)
            """,

            [

            (
            "DIPAC White Party",
            "2026-06-14",
            "Jakarta",
            "Nightlife"
            ),


            (
            "DIPAC After Hours",
            "2026-05-18",
            "Jakarta",
            "Music"
            )

            ]

            )



            con.executemany(

            """
            INSERT INTO event_metrics
            VALUES(NULL,?,?,?,?,?)
            """,

            [

            (
            1,
            128500000,
            48700000,
            842,
            468
            ),

            (
            2,
            97300000,
            36100000,
            714,
            387
            )

            ]

            )



            con.executemany(

            """
            INSERT INTO ai_insights
            VALUES(NULL,?,?,?)
            """,

            [

            (
            1,
            "Premium table package menjadi penggerak nilai transaksi tertinggi. Pertahankan early access untuk member.",
            datetime.now(timezone.utc).isoformat()
            ),

            (
            2,
            "Format After Hours menarik repeat audience yang kuat. Tambahkan kapasitas VIP secara bertahap pada edisi berikutnya.",
            datetime.now(timezone.utc).isoformat()
            )

            ]

            )



# ==========================
# MULTIPART PARSING
# ==========================

def parse_multipart(body, boundary):

    boundary_bytes = ("--" + boundary).encode()

    parts = body.split(boundary_bytes)

    fields = {}

    files = {}


    for part in parts:

        part = part.strip(b"\r\n")

        if not part or part == b"--":
            continue

        header_end = part.find(b"\r\n\r\n")

        if header_end == -1:
            continue

        headers_raw = part[:header_end].decode("utf-8", errors="replace")

        content = part[header_end + 4:]

        if content.endswith(b"\r\n"):
            content = content[:-2]

        name = None
        filename = None

        for line in headers_raw.split("\r\n"):

            if line.lower().startswith("content-disposition"):

                for piece in line.split(";")[1:]:

                    key, _, val = piece.strip().partition("=")

                    val = val.strip('"')

                    if key == "name":
                        name = val

                    elif key == "filename":
                        filename = val


        if name is None:
            continue

        if filename:
            files[name] = (filename, content)

        else:
            fields[name] = content.decode("utf-8", errors="replace")


    return fields, files



# ==========================
# SESSION
# ==========================

def verify_password(
    password,
    stored
):

    if "$" in stored:

        salt, derived = stored.split("$", 1)

        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            200_000
        ).hex()

        return secrets.compare_digest(candidate, derived)


    # legacy unsalted sha256 hash from older builds - verified once,
    # then the login handler upgrades it to the salted format above
    legacy = hashlib.sha256(
        password.encode()
    ).hexdigest()

    return secrets.compare_digest(legacy, stored)



sessions = {}

SESSION_HOURS = 12

MAX_LOGIN_ATTEMPTS = 5

LOGIN_LOCKOUT_MINUTES = 15

login_attempts = {}



def login_is_locked(email):

    entry = login_attempts.get(email)

    if not entry:
        return False

    count, first_attempt = entry

    elapsed = (datetime.now(timezone.utc) - first_attempt).total_seconds() / 60

    if elapsed > LOGIN_LOCKOUT_MINUTES:

        login_attempts.pop(email, None)

        return False


    return count >= MAX_LOGIN_ATTEMPTS



def register_failed_login(email):

    count, first_attempt = login_attempts.get(
        email,
        (0, datetime.now(timezone.utc))
    )

    login_attempts[email] = (count + 1, first_attempt)



def clear_failed_login(email):

    login_attempts.pop(email, None)


# ==========================
# SERVER HANDLER
# ==========================

class AppHandler(SimpleHTTPRequestHandler):


    def __init__(self, *args, **kwargs):

        super().__init__(
            *args,
            directory=str(ROOT),
            **kwargs
        )



    def send_json(
        self,
        data,
        status=200,
        cookie=None
    ):

        body = json.dumps(
            data
        ).encode()


        self.send_response(
            status
        )


        self.send_header(
            "Content-Type",
            "application/json"
        )


        self.send_header(
            "Content-Length",
            str(len(body))
        )


        if cookie:

            self.send_header(
                "Set-Cookie",
                cookie
            )


        self.end_headers()


        self.wfile.write(
            body
        )



    def body(self):

        length = int(
            self.headers.get(
                "Content-Length",
                0
            )
        )


        if length:

            return json.loads(
                self.rfile.read(length)
            )


        return {}



    def current_user(self):

        cookie = SimpleCookie(
            self.headers.get("Cookie")
        )


        if "dipac_session" not in cookie:

            return None



        token = cookie[
            "dipac_session"
        ].value


        session = sessions.get(token)

        if not session:
            return None


        if datetime.now(timezone.utc) > session["expires_at"]:

            sessions.pop(token, None)

            return None


        return session["email"]



    # ======================
    # LOGIN
    # ======================

    def do_POST(self):


        route = urlparse(
            self.path
        ).path



        if route == "/api/login":


            data = self.body()


            email = data.get(
                "email"
            )


            password = data.get(
                "password"
            )



            if login_is_locked(email):

                return self.send_json(
                {
                "error":
                f"Terlalu banyak percobaan gagal. Coba lagi dalam {LOGIN_LOCKOUT_MINUTES} menit."
                },
                429
                )



            with db() as con:

                user = con.execute(
                """
                SELECT *
                FROM users
                WHERE email=?
                """,
                (email,)
                ).fetchone()



            if not user:

                register_failed_login(email)

                return self.send_json(
                {
                "error":
                "Email tidak ditemukan"
                },
                401
                )



            if not verify_password(
                password,
                user["password_hash"]
            ):

                register_failed_login(email)

                return self.send_json(
                {
                "error":
                "Password salah"
                },
                401
                )


            clear_failed_login(email)


            # auto-upgrade a legacy unsalted hash to the salted format
            # now that we know the plaintext password matched it
            if "$" not in user["password_hash"]:

                with db() as con:

                    con.execute(
                    "UPDATE users SET password_hash=? WHERE email=?",
                    (password_hash(password), email)
                    )



            token = secrets.token_hex(
                32
            )


            sessions[token] = {

            "email": email,

            "expires_at": datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)

            }



            return self.send_json(
            {
            "success": True
            },
            cookie=
            f"dipac_session={token}; Path=/; HttpOnly; Max-Age={SESSION_HOURS * 3600}"
            )



        if route == "/api/logout":


            cookie = SimpleCookie(
                self.headers.get("Cookie")
            )


            if "dipac_session" in cookie:

                sessions.pop(
                    cookie["dipac_session"].value,
                    None
                )


            return self.send_json(
            {
            "success": True
            },
            cookie=
            "dipac_session=; Path=/; Max-Age=0"
            )



        if route == "/api/change-password":


            email = self.current_user()

            if not email:

                return self.send_json(
                {
                "error": "Unauthorized"
                },
                401
                )


            data = self.body()

            current_password = data.get("current_password") or ""

            new_password = data.get("new_password") or ""


            if len(new_password) < 8:

                return self.send_json(
                {
                "error": "Password baru minimal 8 karakter"
                },
                400
                )


            with db() as con:

                user = con.execute(
                """
                SELECT * FROM users WHERE email=?
                """,
                (email,)
                ).fetchone()


            if not verify_password(current_password, user["password_hash"]):

                return self.send_json(
                {
                "error": "Password saat ini salah"
                },
                401
                )


            with db() as con:

                con.execute(
                "UPDATE users SET password_hash=? WHERE email=?",
                (password_hash(new_password), email)
                )


            return self.send_json(
            {
            "success": True
            }
            )



        if route == "/api/upload-report":


            if not self.current_user():

                return self.send_json(
                {
                "error": "Unauthorized"
                },
                401
                )


            content_type = self.headers.get("Content-Type", "")

            if "multipart/form-data" not in content_type or "boundary=" not in content_type:

                return self.send_json(
                {
                "error": "Format unggahan tidak valid"
                },
                400
                )


            length = int(self.headers.get("Content-Length", 0))

            if length <= 0 or length > MAX_REPORT_SIZE:

                return self.send_json(
                {
                "error": "Ukuran file tidak valid atau terlalu besar (maks 20MB)"
                },
                413
                )


            boundary = content_type.split("boundary=")[-1].strip('"')

            raw_body = self.rfile.read(length)

            fields, files = parse_multipart(raw_body, boundary)


            if "report" not in files:

                return self.send_json(
                {
                "error": "PDF report wajib diunggah"
                },
                400
                )


            original_name, file_content = files["report"]

            safe_name = f"{secrets.token_hex(12)}-{Path(original_name).name}"

            upload_path = UPLOAD_DIR / safe_name

            upload_path.write_bytes(file_content)


            text = extract_pdf_text(upload_path)

            analysis = analyze_report(text)


            event_name = fields.get("event_name") or analysis.get("event_name") or "Untitled Event"

            event_date = fields.get("event_date") or analysis.get("date") or None

            location = fields.get("location") or analysis.get("location") or None


            transactions = analysis.get("transactions", [])

            with db() as con:

                cursor = con.execute(
                """
                INSERT INTO reports
                (event_id, file_name, event_name, event_date, location, pax, revenue, cost, profit, analysis, insights_json, created_at)
                VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                safe_name,
                event_name,
                event_date,
                location,
                analysis.get("pax", 0),
                analysis.get("revenue", 0),
                analysis.get("cost", 0),
                analysis.get("profit", 0),
                analysis.get("insight", ""),
                json.dumps(analysis.get("insight_list", [])),
                datetime.now(timezone.utc).isoformat(),
                )
                )

                report_id = cursor.lastrowid

                if transactions:

                    con.executemany(
                    """
                    INSERT INTO transactions
                    (report_id, category, menu, qty, customer_price, customer_revenue, collective_share, commission_pct, profit)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    [
                    (
                    report_id,
                    t["category"],
                    t["menu"],
                    t["qty"],
                    t["customer_price"],
                    t["customer_revenue"],
                    t["collective_share"],
                    t["commission_pct"],
                    t["profit"],
                    )
                    for t in transactions
                    ]
                    )


            response_analysis = dict(analysis)

            response_analysis["event_name"] = event_name

            response_analysis["event_date"] = event_date

            response_analysis["location"] = location

            response_analysis["report_id"] = report_id


            return self.send_json(
            {
            "success": True,
            "analysis": response_analysis
            }
            )



        return self.send_json(
        {
        "error": "Not found"
        },
        404
        )



    # ======================
    # GET
    # ======================

    def do_GET(self):


        route = urlparse(
            self.path
        ).path



        # HOME PAGE

        if route == "/":

            self.path = "/frontend/index.html"

            return super().do_GET()



        # DASHBOARD API

        if route == "/api/dashboard":


            if not self.current_user():

                return self.send_json(
                {
                "error": "Unauthorized"
                },
                401
                )



            with db() as con:


                events = con.execute(
                """
                SELECT
                e.name,
                e.event_date,
                e.location,
                e.category,
                m.pax,
                m.total_revenue,
                m.total_profit
                FROM events e
                JOIN event_metrics m
                ON e.id=m.event_id
                ORDER BY e.id DESC
                """
                ).fetchall()



                event_totals = con.execute(
                """
                SELECT

                SUM(total_revenue) revenue,

                SUM(total_profit) profit,

                SUM(pax) pax,

                SUM(transactions) transactions

                FROM event_metrics

                """
                ).fetchone()


                report_totals = con.execute(
                """
                SELECT

                SUM(revenue) revenue,

                SUM(profit) profit,

                SUM(pax) pax

                FROM reports

                """
                ).fetchone()


                report_transaction_count = con.execute(
                """
                SELECT COUNT(*) FROM transactions
                """
                ).fetchone()[0]


                totals = {

                "revenue": (event_totals["revenue"] or 0) + (report_totals["revenue"] or 0),

                "profit": (event_totals["profit"] or 0) + (report_totals["profit"] or 0),

                "pax": (event_totals["pax"] or 0) + (report_totals["pax"] or 0),

                "transactions": (event_totals["transactions"] or 0) + report_transaction_count

                }



                insights = con.execute(
                """
                SELECT
                COALESCE(e.name, 'DIPAC Society') AS name,
                ai.recommendation AS recommendation
                FROM ai_insights ai
                LEFT JOIN events e
                ON e.id = ai.event_id
                ORDER BY ai.id DESC
                """
                ).fetchall()



            return self.send_json(
            {

            "user":
            { "name": "DIPAC Administrator" },

            "totals":
            totals,


            "events":
            [
            dict(x)
            for x in events
            ],


            "insights":
            [
            dict(x)
            for x in insights
            ]

            }

            )



        # REPORTS API

        if route == "/api/reports":


            if not self.current_user():

                return self.send_json(
                {
                "error": "Unauthorized"
                },
                401
                )


            with db() as con:

                reports = con.execute(
                """
                SELECT
                id,
                event_name AS event,
                event_date,
                location,
                pax,
                revenue,
                cost,
                profit,
                analysis AS insight,
                file_name,
                created_at
                FROM reports
                ORDER BY created_at DESC
                """
                ).fetchall()


            return self.send_json(
            [
            dict(x)
            for x in reports
            ]
            )



        # SINGLE EVENT ANALYSIS (report + its line-item transactions)

        if route == "/api/event-analysis":


            if not self.current_user():

                return self.send_json(
                {
                "error": "Unauthorized"
                },
                401
                )


            query = parse_qs(urlparse(self.path).query)

            report_id = query.get("report_id", [None])[0]

            if not report_id:

                return self.send_json(
                {
                "error": "report_id wajib diisi"
                },
                400
                )


            with db() as con:

                report = con.execute(
                """
                SELECT * FROM reports WHERE id=?
                """,
                (report_id,)
                ).fetchone()


                if not report:

                    return self.send_json(
                    {
                    "error": "Report tidak ditemukan"
                    },
                    404
                    )


                transactions = con.execute(
                """
                SELECT * FROM transactions WHERE report_id=? ORDER BY id
                """,
                (report_id,)
                ).fetchall()


            report_dict = dict(report)

            try:

                report_dict["insight_list"] = json.loads(report_dict.get("insights_json") or "[]")

            except json.JSONDecodeError:

                report_dict["insight_list"] = []


            bottle_qty = sum(t["qty"] for t in transactions if t["category"] == "Bottle")

            avg_spending = round(report_dict["revenue"] / report_dict["pax"]) if report_dict.get("pax") else 0

            commission_rate = round(report_dict["profit"] / report_dict["revenue"] * 100, 2) if report_dict.get("revenue") else 0


            return self.send_json(
            {

            "report": report_dict,

            "metrics":
            {
            "customer_spending": report_dict["revenue"],
            "collective_income": report_dict["profit"],
            "bottle_sold": bottle_qty,
            "average_spending": avg_spending,
            "profit_contribution": report_dict["profit"],
            "commission_rate": commission_rate
            },

            "transactions":
            [
            dict(t)
            for t in transactions
            ]

            }
            )



        # EVENT COMPARISON (across all uploaded reports)

        if route == "/api/event-comparison":


            if not self.current_user():

                return self.send_json(
                {
                "error": "Unauthorized"
                },
                401
                )


            with db() as con:

                reports = con.execute(
                """
                SELECT id, event_name, event_date, location, pax, revenue, profit
                FROM reports
                ORDER BY created_at DESC
                """
                ).fetchall()


            reports = [dict(r) for r in reports]

            total_spending = sum(r["revenue"] or 0 for r in reports)

            total_income = sum(r["profit"] or 0 for r in reports)

            avg_commission = round(total_income / total_spending * 100, 2) if total_spending else 0

            best = max(reports, key=lambda r: r["profit"] or 0) if reports else None


            return self.send_json(
            {

            "totals":
            {
            "total_customer_spending": total_spending,
            "total_collective_income": total_income,
            "average_commission": avg_commission,
            "best_event": best["event_name"] if best else None
            },

            "events": reports

            }
            )



        # DASHBOARD PAGE

        if route == "/dashboard":


            if not self.current_user():

                self.send_response(
                    302
                )

                self.send_header(
                    "Location",
                    "/"
                )

                self.end_headers()

                return



            self.path = "/frontend/dashboard.html"



        return super().do_GET()




# ==========================
# RUN SERVER
# ==========================

if __name__ == "__main__":


    init_db()


    print(
    "DIPAC Society running at http://localhost:8000"
    )


    ThreadingHTTPServer(
    (
    "0.0.0.0",
    PORT
    ),

    AppHandler

    ).serve_forever()
