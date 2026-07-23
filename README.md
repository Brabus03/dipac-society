# DIPAC Society

Landing page publik + DIPAC Intelligence Dashboard privat untuk event promotion business, dengan fitur import & analisis PDF report otomatis. Dibangun full-stack dengan Python standard library saja (tanpa framework) di sisi server, dan vanilla HTML/CSS/JS di sisi client.

## Stack

- **Backend**: Python `http.server` (ThreadingHTTPServer) + SQLite, tanpa framework
- **Frontend**: Vanilla HTML/CSS/JS, tanpa build step
- **AI/Parsing**: Ekstraksi & analisis PDF report offline (regex-based, tanpa API key eksternal)
- **Auth**: Salted PBKDF2 password hashing, session expiry, login rate-limiting
- **Deploy**: systemd + Caddy reverse proxy di VPS Ubuntu

## Struktur

```
backend/app.py      - server (stdlib http.server + SQLite)
frontend/            - HTML/CSS/JS (landing page + dashboard)
ai/                   - ekstraksi teks PDF & analisis metrik event
data/                 - dipac.db (dibuat otomatis saat pertama jalan, tidak di-commit)
assets/               - gambar & video
reports/, uploads/    - hasil parsing & file PDF yang diunggah (tidak di-commit)
deploy/               - systemd service, Caddyfile, dan runbook deploy
```

## Jalankan

```bash
cd dipac-society
python3 -m pip install -r requirements.txt   # opsional, untuk baca PDF report
python3 backend/app.py
```

Buka `http://localhost:8000`.

## Akun awal

Saat server pertama kali dijalankan dan belum ada user di database, akun admin dibuat otomatis:

- Email: `admin@dipac.co`
- Password: diambil dari environment variable `DIPAC_ADMIN_PASSWORD` kalau di-set; kalau tidak, sistem generate password acak dan menampilkannya sekali di log server saat startup.

```bash
DIPAC_ADMIN_PASSWORD="password-kamu-sendiri" python3 backend/app.py
```

Password bisa diganti kapan saja lewat halaman **Account** di dashboard. Halaman publik sengaja tidak memaparkan revenue, transaksi, pax, atau analitik internal — semua itu ada di balik login.

## Fitur AI Analyzer

Di dashboard (`Overview → AI Analyzer`), unggah PDF report event untuk otomatis:
- Ekstrak revenue, cost, profit, pax, ticket sales, bottle sales dari teks PDF (regex offline, tanpa API key)
- Hitung profit margin & revenue per pax
- Generate rekomendasi strategi bahasa Indonesia

Kalau `PyMuPDF`/`pdfplumber` tidak terpasang, sistem otomatis coba `pdftotext` (poppler) sebagai fallback; kalau tetap tidak ada, ekstraksi teks akan kosong dan analisis akan meminta report yang lebih lengkap.
