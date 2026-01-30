import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import logging

logger = logging.getLogger(__name__)

CACHE_FILE = 'history_data.json'

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
    return {"dates": [], "prices": []}

def save_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def get_historical_data():
    """
    Fetches historical gold price data (Bank Buys) from Bank of Taiwan LTM page.
    LTM: https://rate.bot.com.tw/gold/chart/ltm/TWD
    """
    cache = load_cache()
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    # If cache has today's data (or at least recent data), return it
    # Note: BOT update might lag, so we check if last entry is today.
    if cache['dates'] and cache['dates'][-1] == today_str:
        logger.info("Historical cache is up to date.")
        return cache

    url = "https://rate.bot.com.tw/gold/chart/ltm/TWD"
    
    try:
        logger.info(f"Fetching historical data from LTM page: {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tbody = soup.find('tbody')
        if not tbody:
            # Maybe there's a specific table class
            table = soup.select_one('table.table-striped')
            if table:
                tbody = table.find('tbody')
        
        if not tbody:
            logger.warning("No tbody found on LTM page.")
            return cache

        entries = []
        rows = tbody.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 4:
                # Column 0: Date (YYYY/MM/DD)
                # Column 3: Bank Buy (Price)
                date_text = tds[0].get_text(strip=True).replace('/', '-')
                price_text = tds[3].get_text(strip=True).replace(',', '')
                try:
                    price = float(price_text)
                    entries.append((date_text, price))
                except ValueError:
                    continue
        
        if not entries:
            logger.warning("No entries parsed from LTM page.")
            return cache

        # LTM page is usually descending (newest first). Let's sort to ascending.
        entries.sort(key=lambda x: x[0])
        
        result = {
            "dates": [e[0] for e in entries],
            "prices": [e[1] for e in entries]
        }
        
        save_cache(result)
        logger.info(f"Historical data updated. Total points: {len(result['dates'])}")
        return result

    except Exception as e:
        logger.error(f"Error fetching historical LTM data: {e}")
        return cache

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = get_historical_data()
    print(f"Total points: {len(data['dates'])}")
    if data['dates']:
        print(f"Latest: {data['dates'][-1]} -> {data['prices'][-1]}")
