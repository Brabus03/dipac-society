"""Offline-first event report data extraction and strategy generation."""
import os
import re


def _to_int(raw):
    """Parse a locale-formatted number string ("56,000,000.00" or "17.391.775")
    into an int, dropping the decimal part instead of concatenating it -
    treating "." as a thousands separator would turn 56,000,000.00 into
    5,600,000,000 (100x too large)."""
    raw = raw.strip().replace(" ", "")
    if "," in raw and "." in raw:
        # whichever separator appears last is the decimal point
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
        raw = raw.split(".")[0]
    elif "," in raw:
        # ambiguous: "17,391,775" (thousands) vs "17,50" (decimal) - treat
        # a trailing group of 1-2 digits as decimal, 3 digits as thousands
        parts = raw.split(",")
        if len(parts[-1]) in (1, 2):
            raw = "".join(parts[:-1])
        else:
            raw = "".join(parts)
    elif "." in raw:
        parts = raw.split(".")
        if len(parts[-1]) in (1, 2):
            raw = "".join(parts[:-1])
        else:
            raw = "".join(parts)
    try:
        return int(raw)
    except ValueError:
        return 0


def _value(text, labels, money=False):
    label = "(?:" + "|".join(re.escape(item) for item in labels) + ")"
    match = re.search(label + r"\s*(?:[:=-]|is)?\s*(?:rp\.?\s*)?([0-9][0-9., ]*)", text, re.I)
    if not match:
        return 0
    return _to_int(match.group(1))


def _text_value(text, labels):
    label = "(?:" + "|".join(re.escape(item) for item in labels) + ")"
    match = re.search(label + r"\s*(?:[:=-])\s*([^\n\r]{2,80})", text, re.I)
    return match.group(1).strip() if match else ""


MONEY = r"(\d[\d,]*\.\d{2})"


def extract_transactions(text):
    """Best-effort line-item extraction from an "ITEM SALES REPORT"-style
    table: <menu name>  <qty>  <price columns...>. Returns a list of dicts,
    empty when the report has no recognizable item table - callers should
    treat that as "no line items available", not an error.
    """
    rows = []

    # Per-menu bottle/item rows: name, qty, then price/revenue/markup/profit
    # columns (5 money values in the "911 X DIPAC"-style FDC/TNF report).
    # Not anchored to line start: side-by-side PDF tables often flatten onto
    # the same text line, so the item row can follow unrelated left-column
    # content - the menu name's char class excludes "," so it can't span
    # across a money value from that other column, and matching is anchored
    # to end-of-line since the item columns are always the last content.
    item_pattern = re.compile(
        r"(?P<menu>[A-Za-z][A-Za-z0-9+.'\- ]{2,60}?)\s{3,}"
        r"(?P<qty>\d{1,4})\s+"
        rf"{MONEY}\s+{MONEY}\s+{MONEY}\s+{MONEY}\s+{MONEY}\s*$"
    )

    for line in text.splitlines():
        match = item_pattern.search(line.rstrip())
        if not match:
            continue

        menu = match.group("menu").strip()
        qty = int(match.group("qty"))
        # Money groups in column order: TNF Price(3), TOTAL TNF REVENUE(4),
        # Publish Price(5), Mark Up(6), Profit Sales(7) - "menu"/"qty" are
        # themselves numbered groups 1-2, so the money groups start at 3.
        unit_price = _to_int(match.group(5))  # Publish Price
        collective_share = _to_int(match.group(6))  # Mark Up
        profit = _to_int(match.group(7))  # Profit Sales
        customer_revenue = unit_price * qty
        commission_pct = round(collective_share / customer_revenue * 100, 2) if customer_revenue else 0

        rows.append({
            "category": "Bottle",
            "menu": menu,
            "qty": qty,
            "customer_price": unit_price,
            "customer_revenue": customer_revenue,
            "collective_share": collective_share,
            "commission_pct": commission_pct,
            "profit": profit,
        })

    # Lump-sum FDC (cover charge) line, when present: "Total FDC <count>",
    # a per-head price, and "TOTAL SHARING <amount>".
    fdc_count = _value(text, ["total fdc"])
    fdc_price = _value(text, ["price before tax"])
    fdc_share = _value(text, ["total sharing"])
    if fdc_count and fdc_price:
        customer_revenue = fdc_count * fdc_price
        rows.append({
            "category": "FDC",
            "menu": "FDC Collective Share",
            "qty": fdc_count,
            "customer_price": fdc_price,
            "customer_revenue": customer_revenue,
            "collective_share": fdc_share,
            "commission_pct": round(fdc_share / customer_revenue * 100, 2) if customer_revenue else 0,
            "profit": fdc_share,
        })

    return rows


def analyze_report(text):
    """Extract a normalized report object and an actionable offline insight."""
    event_name = _text_value(text, ["event name", "event", "nama event"])
    event_date = _text_value(text, ["event date", "date", "tanggal event", "tanggal"])
    location = _text_value(text, ["location", "venue", "lokasi"])
    pax = _value(text, ["total guest", "total guests", "total pax", "pax", "attendees", "guests", "pengunjung"])
    revenue = _value(text, ["total revenue", "revenue", "gross sales", "pendapatan"], True)
    cost = _value(text, ["total cost", "total costs", "cost", "biaya total", "operational cost"], True)
    profit = _value(text, ["net profit", "profit", "laba bersih", "laba"], True)
    ticket_sales = _value(text, ["ticket sales", "ticket sold", "tiket terjual", "penjualan tiket"])
    bottle_sales = _value(text, ["bottle sales", "bottle sold", "botol terjual", "penjualan botol"])
    vendor_cost = _value(text, ["vendor cost", "biaya vendor"], True)
    artist_fee = _value(text, ["artist fee", "talent fee", "biaya artis"], True)
    if not profit and revenue and cost:
        profit = max(revenue - cost, 0)

    transactions = extract_transactions(text)
    if transactions:
        if not revenue:
            revenue = sum(t["customer_revenue"] for t in transactions)
        if not profit:
            profit = sum(t["collective_share"] for t in transactions)
        if not bottle_sales:
            bottle_sales = sum(t["qty"] for t in transactions if t["category"] == "Bottle")

    insights = []
    if revenue and pax:
        insights.append(f"Revenue per pax sekitar Rp{revenue // max(pax, 1):,}.")
    if profit and revenue:
        margin = round(profit / revenue * 100)
        insights.append(f"Profit margin {margin}%.")
        if margin < 20:
            insights.append("Evaluasi vendor cost dan artist fee sebelum event berikutnya.")
        else:
            insights.append("Pertahankan struktur biaya dan tambah kapasitas VIP atau table package.")
    if transactions:
        best = max(transactions, key=lambda t: t["collective_share"])
        insights.append(f"Menu dengan kontribusi collective terbesar: {best['menu']}. Gunakan sebagai benchmark event berikutnya.")
    elif bottle_sales:
        insights.append(f"Bottle sales tercatat {bottle_sales}; siapkan bundling premium dan pre-order untuk menaikkan basket size.")
    if ticket_sales and pax and ticket_sales < pax:
        insights.append("Perkuat check-in dan upsell walk-in agar konversi tiket sesuai jumlah pax.")
    if not insights:
        insights.append("Metrik utama belum lengkap. Pastikan report mencantumkan Revenue, Cost, Profit, Pax, dan penjualan tiket atau botol.")

    return {
        "event_name": event_name,
        "date": event_date,
        "location": location,
        "pax": pax,
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "ticket_sales": ticket_sales,
        "bottle_sales": bottle_sales,
        "vendor_cost": vendor_cost,
        "artist_fee": artist_fee,
        "insight": " ".join(insights),
        "insight_list": insights,
        "transactions": transactions,
    }


def analyze_with_ai(text):
    """Optional integration hook. Offline analysis remains the default."""
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        return None
    return None
