import requests
import json
from datetime import datetime
import socket
import sys
from typing import Dict, List, Optional

# ========================
# CONFIGURATION
# ========================
DEFAULT_API = "https://api.exchangerate-api.com/v4/latest/USD"
BACKUP_APIS = [
    "https://api.coindesk.com/v2/bpi/currentprice.json",
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur,gbp,jpy,cny",
    "https://blockchain.info/ticker",
    "https://api.coinbase.com/v2/exchange-rates?currency=BTC"
]
REPORT_FILE = "btc_price_report.txt"
TIMEOUT = 10  # seconds

CURRENCY_SYMBOLS = {
    'USD': '$', 'GBP': '£', 'EUR': '€',
    'JPY': '¥', 'CNY': '¥', 'BTC': '₿'
}

# ========================
# CORE FUNCTIONS
# ========================
def check_internet() -> bool:
    """Verify internet connectivity"""
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=3)
        return True
    except OSError:
        return False

def fetch_data(url: str) -> Optional[dict]:
    """Fetch JSON data from API with robust error handling"""
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ API Error ({url}): {type(e).__name__} - {str(e)}", file=sys.stderr)
        return None

def parse_response(data: dict, source: str) -> Optional[Dict[str, str]]:
    """Parse different API response formats"""
    try:
        if "coindesk" in source:
            return {curr: info["rate"] for curr, info in data.get("bpi", {}).items()}
        elif "coingecko" in source:
            return {curr.upper(): str(price) for curr, price in data.get("bitcoin", {}).items()}
        elif "blockchain" in source:
            return {curr: str(info["last"]) for curr, info in data.items()}
        elif "coinbase" in source:
            return {curr: str(rate) for curr, rate in data.get("data", {}).get("rates", {}).items()
                    if curr != "BTC"}
    except (KeyError, AttributeError) as e:
        print(f"⚠️ Parsing Error: {type(e).__name__} - {str(e)}", file=sys.stderr)
    return None

def format_price(currency: str, price: str) -> str:
    """Format price with symbol and thousands separator"""
    symbol = CURRENCY_SYMBOLS.get(currency, '')
    try:
        clean_price = price.replace(",", "")
        formatted = f"{float(clean_price):,.2f}"
        return f"{symbol}{formatted}"
    except ValueError:
        return f"{symbol}{price}"

# ========================
# USER INTERFACE
# ========================
def get_user_input(prompt: str, default: str = "") -> str:
    """Get input with default value support"""
    user_input = input(prompt).strip()
    return user_input if user_input else default

def select_currencies(available: List[str]) -> List[str]:
    """Let user select currencies with validation"""
    print("\nAvailable currencies:", ", ".join(sorted(available)))
    while True:
        selection = get_user_input(
            "Enter currency codes (comma-separated)\n"
            "or press Enter for all: "
        ).upper()

        if not selection:
            return available

        selected = [c.strip() for c in selection.split(",")]
        invalid = [c for c in selected if c not in available]

        if not invalid:
            return selected
        print(f"Invalid currencies: {', '.join(invalid)}. Please try again.")

# ========================
# REPORT GENERATION
# ========================
def generate_report(prices: Dict[str, str], filename: str = REPORT_FILE) -> bool:
    """Generate formatted price report"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"""📊 BITCOIN PRICE REPORT
{"-"*40}
Generated: {timestamp}
{"-"*40}\n""")
            for currency in sorted(prices.keys()):
                f.write(f"{currency}: {format_price(currency, prices[currency])}\n")
        return True
    except IOError as e:
        print(f"⚠️ File Error: {type(e).__name__} - {str(e)}", file=sys.stderr)
        return False

# ========================
# MAIN EXECUTION
# ========================
def main():
    print("₿ Bitcoin Price Fetcher")
    print("-" * 40)

    if not check_internet():
        print("❌ No internet connection detected", file=sys.stderr)
        input("Press Enter to exit...")
        return

    api_url = get_user_input(
        f"Enter API URL (press Enter for default)\n"
        f"Default: {DEFAULT_API}\n"
        "> "
    ) or DEFAULT_API

    prices = None
    for attempt, url in enumerate([api_url] + BACKUP_APIS, 1):
        print(f"\nAttempt {attempt}: Fetching from {url}")
        data = fetch_data(url)
        if data:
            prices = parse_response(data, url)
            if prices:
                break

    if not prices:
        print("\n❌ All API attempts failed. Possible solutions:", file=sys.stderr)
        print("1. Check your internet connection")
        print("2. Try again later (APIs might be down)")
        print("3. Use a VPN (might bypass network restrictions)")
        input("\nPress Enter to exit...")
        return

    selected = select_currencies(list(prices.keys()))
    filtered_prices = {k: v for k, v in prices.items() if k in selected}

    print("\nCurrent Bitcoin Prices:")
    for curr, price in filtered_prices.items():
        print(f"  {curr}: {format_price(curr, price)}")

    if generate_report(filtered_prices):
        print(f"\n✅ Report saved to {REPORT_FILE}")

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
