#!/usr/bin/env python3
"""
Expense Tracker (Console)
SQLite + Pandas + Matplotlib + CSV/PDF + Real-time Budget Alerts + Saved Charts

Menu:
1. Add Expense
2. View All Expenses
3. Filter by Category
4. Filter by Date
5. Monthly Summary (with budget alert)
6. Show Pie Chart (category distribution)  [also saves PNG]
7. Show Bar Chart (monthly trend)          [also saves PNG]
8. Export to CSV
9. Export to PDF (includes charts if available)
10. Exit
"""

import os
import sys
import sqlite3
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# =============== CONFIG ===============
DB_FILE = "expenses.db"
REPORT_DIR = "reports"
CHART_DIR = os.path.join(REPORT_DIR, "charts")
MONTHLY_BUDGET = 5000.0  # change as you like
CURRENCY = "₹"           # change to "$" or "€" etc.

# =============== SETUP ===============
def ensure_dirs():
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(CHART_DIR, exist_ok=True)

def get_connection():
    return sqlite3.connect(DB_FILE)

def initialize_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT
        )
        """
    )
    conn.commit()
    conn.close()

# =============== HELPERS ===============
def fetch_all_df():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, amount, category, date, description FROM expenses ORDER BY date DESC, id DESC",
        conn,
    )
    conn.close()
    return df

def valid_date_yyyy_mm_dd(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# =============== FEATURES ===============
def add_expense():
    try:
        amount = float(input("Enter amount: ").strip())
    except ValueError:
        print("⚠  Invalid amount. Use numbers only.")
        return

    category = input("Enter category: ").strip() or "Uncategorized"
    date_input = input("Enter date (YYYY-MM-DD) [leave blank for today]: ").strip()
    if date_input:
        if not valid_date_yyyy_mm_dd(date_input):
            print("⚠  Invalid date format. Use YYYY-MM-DD.")
            return
        date_str = date_input
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    description = input("Enter description: ").strip()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (amount, category, date, description) VALUES (?, ?, ?, ?)",
        (amount, category, date_str, description),
    )
    conn.commit()
    conn.close()
    print("✅ Expense added successfully!")

    check_budget_alert_for_date(date_str)

def view_all_expenses():
    df = fetch_all_df()
    if df.empty:
        print("No expenses found.\n")
        return
    print(tabulate(df, headers="keys", tablefmt="pretty", showindex=False))
    print()

def filter_by_category():
    category = input("Enter category to filter: ").strip()
    if not category:
        print("⚠  Please enter a category.")
        return
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, amount, category, date, description FROM expenses WHERE category = ? ORDER BY date DESC, id DESC",
        conn,
        params=(category,),
    )
    conn.close()
    if df.empty:
        print("No expenses found for this category.\n")
        return
    print(tabulate(df, headers="keys", tablefmt="pretty", showindex=False))
    print()

def filter_by_date():
    date_str = input("Enter date (YYYY-MM-DD) to filter: ").strip()
    if not valid_date_yyyy_mm_dd(date_str):
        print("⚠  Invalid date format. Use YYYY-MM-DD.")
        return
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, amount, category, date, description FROM expenses WHERE date = ? ORDER BY id DESC",
        conn,
        params=(date_str,),
    )
    conn.close()
    if df.empty:
        print("No expenses found for this date.\n")
        return
    print(tabulate(df, headers="keys", tablefmt="pretty", showindex=False))
    print()

def monthly_summary():
    df = fetch_all_df()
    if df.empty:
        print("No expenses to summarize.\n")
        return

    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    summary = df.groupby("month", as_index=False)["amount"].sum()
    summary["month"] = summary["month"].astype(str)

    print("\n📅 Monthly Expense Summary:")
    print(tabulate(summary, headers=["month", "amount"], tablefmt="pretty", showindex=False))

    latest = summary.iloc[-1]
    latest_month = latest["month"]
    latest_total = float(latest["amount"])
    print(f"\nLatest month: {latest_month} — Total: {CURRENCY}{latest_total:,.2f}")
    if latest_total > MONTHLY_BUDGET:
        print("⚠ ALERT: Monthly budget exceeded!")
    print()

# ---- Charts (both show and save PNG) ----
def save_and_optionally_show(fig, filename, show=True):
    ensure_dirs()
    path = os.path.join(CHART_DIR, filename)
    fig.savefig(path, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close(fig)
    print(f"🖼  Chart saved to {path}")
    return path

def show_pie_chart(show=True):
    df = fetch_all_df()
    if df.empty:
        print("No expenses to plot.\n")
        return None
    cat_sum = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7, 7))
    cat_sum.plot.pie(autopct="%1.1f%%", startangle=90, ax=ax)
    ax.set_title("Expense Distribution by Category")
    ax.set_ylabel("")
    fname = f"pie_category_{timestamp()}.png"
    return save_and_optionally_show(fig, fname, show=show)

def show_bar_chart(show=True):
    df = fetch_all_df()
    if df.empty:
        print("No expenses to plot.\n")
        return None
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    month_sum = df.groupby("month")["amount"].sum().sort_index()
    fig, ax = plt.subplots(figsize=(9, 5))
    month_sum.plot(kind="bar", ax=ax)
    ax.set_title("Monthly Spending Trends")
    ax.set_xlabel("Month")
    ax.set_ylabel(f"Total Spending ({CURRENCY})")
    plt.xticks(rotation=45)
    fname = f"bar_monthly_{timestamp()}.png"
    return save_and_optionally_show(fig, fname, show=show)

def option_show_pie_chart():
    path = show_pie_chart(show=True)
    if path is None:
        return

def option_show_bar_chart():
    path = show_bar_chart(show=True)
    if path is None:
        return

# ---- Exports ----
def export_to_csv():
    ensure_dirs()
    df = fetch_all_df()
    if df.empty:
        print("No expenses to export.\n")
        return
    filename = os.path.join(REPORT_DIR, f"expenses_{timestamp()}.csv")
    df.to_csv(filename, index=False)
    print(f"✅ Data exported to {filename}")

def export_to_pdf():
    ensure_dirs()
    df = fetch_all_df()
    if df.empty:
        print("No expenses to export.\n")
        return

    # Generate fresh charts (saved, not shown)
    pie_path = show_pie_chart(show=False)
    bar_path = show_bar_chart(show=False)

    filename = os.path.join(REPORT_DIR, f"expenses_{timestamp()}.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    left = 50
    y = height - 50

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, y, "Expense Report")
    y -= 22
    c.setFont("Helvetica", 9)
    c.drawString(left, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 18

    # Totals
    total_amount = df["amount"].sum()
    c.drawString(left, y, f"Total expenses: {CURRENCY}{total_amount:,.2f}")
    y -= 16

    # Category breakdown
    cat_break = df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    c.drawString(left, y, "Category breakdown:")
    y -= 14
    for _, row in cat_break.iterrows():
        c.drawString(left + 10, y, f"- {row['category']}: {CURRENCY}{row['amount']:,.2f}")
        y -= 14
        if y < 120:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)

    # Insert charts if available
    def add_image(path, y_current):
        if path and os.path.exists(path):
            img = ImageReader(path)
            iw, ih = img.getSize()
            max_w = width - 2*left
            max_h = 250
            scale = min(max_w / iw, max_h / ih)
            w, h = iw * scale, ih * scale
            if y_current - h < 80:
                c.showPage()
                y_current = height - 50
            c.drawImage(path, left, y_current - h, width=w, height=h)
            y_current -= (h + 20)
        return y_current

    y = add_image(pie_path, y)
    y = add_image(bar_path, y)

    # Details section
    if y < 120:
        c.showPage()
        y = height - 50
    c.drawString(left, y, "Details:")
    y -= 12
    c.setFont("Helvetica", 8)
    c.drawString(left, y, f"{'Date':<12} {'Category':<15} {'Amount':<12} Description")
    y -= 10
    c.line(left, y + 6, width - left, y + 6)

    for _, row in df.iterrows():
        date_s = str(row["date"])
        cat_s = str(row["category"])[:15]
        amt_s = f"{CURRENCY}{row['amount']:,.2f}"
        desc_s = (str(row["description"]) if row["description"] else "")[:70]
        c.drawString(left, y, f"{date_s:<12} {cat_s:<15} {amt_s:<12} {desc_s}")
        y -= 12
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 8)
            c.drawString(left, y, f"{'Date':<12} {'Category':<15} {'Amount':<12} Description")
            y -= 10
            c.line(left, y + 6, width - left, y + 6)

    c.save()
    print(f"✅ PDF exported to {filename}")

# =============== BUDGET ALERT ===============
def check_budget_alert_for_date(date_str: str):
    try:
        when = pd.to_datetime(date_str)
    except Exception:
        return
    df = fetch_all_df()
    if df.empty:
        return
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    month = when.to_period("M")
    total_month = df[df["month"] == month]["amount"].sum()
    if total_month > MONTHLY_BUDGET:
        print("⚠ ALERT: Monthly budget exceeded!")

# =============== CLI ===============
def print_menu():
    print("\n===== Expense Tracker =====")
    print("1. Add Expense")
    print("2. View All Expenses")
    print("3. Filter by Category")
    print("4. Filter by Date")
    print("5. Monthly Summary")
    print("6. Show Pie Chart")
    print("7. Show Bar Chart")
    print("8. Export to CSV")
    print("9. Export to PDF")
    print("10. Exit")

def main():
    ensure_dirs()
    initialize_db()
    while True:
        print_menu()
        choice = input("Enter choice: ").strip()
        if choice == "1":
            add_expense()
        elif choice == "2":
            view_all_expenses()
        elif choice == "3":
            filter_by_category()
        elif choice == "4":
            filter_by_date()
        elif choice == "5":
            monthly_summary()
        elif choice == "6":
            option_show_pie_chart()
        elif choice == "7":
            option_show_bar_chart()
        elif choice == "8":
            export_to_csv()
        elif choice == "9":
            export_to_pdf()
        elif choice == "10":
            print("Exiting... Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")

if _name_ == "_main_":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        sys.exit(0)