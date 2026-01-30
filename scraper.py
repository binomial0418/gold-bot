import requests
from bs4 import BeautifulSoup
import logging
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_gold_price():
    """
    Fetches gold prices from Bank of Taiwan.
    Returns a dictionary containing gold passbook and physical gold bar prices.
    """
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    
    try:
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
    except Exception:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        result = {
            "passbook": {
                "buy": None,  # Bank Buys (User Sells)
                "sell": None  # Bank Sells (User Buys)
            },
            "physical": {
                "buy": None,  # Bank Buys (User Sells)
            },
            "timestamp": None
        }

        # 1. Parse Gold Passbook (Gram)
        # Using selector `td.text-right.ebank`. 
        # HTML structure: <td> Price <form>...</form> </td>.
        # We need to extract just the price part.
        ebank_cells = soup.select('td.text-right.ebank')
        if len(ebank_cells) >= 2:
            # First cell is "本行賣出" (Bank Sells to User)
            # Second cell is "本行買進" (Bank Buys from User)
            
            def extract_price(cell):
                # cell.get_text() might return "5276買進". We want "5276".
                # Usually the price is the first text node.
                text = cell.get_text(separator=' ', strip=True)
                # Split by space and take first part, or filter digits.
                # "5276 買進" -> "5276"
                parts = text.split()
                if parts:
                    return parts[0]
                return None

            result['passbook']['sell'] = extract_price(ebank_cells[0])
            result['passbook']['buy'] = extract_price(ebank_cells[1])

        # 2. Parse Physical Gold Bar (1 Tael)
        # Find the specific table for "臺銀金鑽條塊" (Diamond Bar).
        # We look for the table containing "臺銀金鑽條塊" but NOT "生肖版" (Zodiac).
        tables = soup.find_all('table')
        for table in tables:
            table_text = table.get_text()
            if "臺銀金鑽條塊" in table_text and "生肖版" not in table_text:
                # Found the correct table.
                # Look for the row with "本行買進".
                rows = table.find_all('tr')
                for row in rows:
                    if "本行買進" in row.get_text():
                        # The price is in `td.text-right`.
                        price_td = row.select_one('td.text-right')
                        if price_td:
                            result['physical']['buy'] = price_td.get_text(strip=True)
                            break
                break

        # Add timestamp
        # Logic: Find div with class "pull-left trailer text-info"
        # Content: "掛牌時間：2023/10/27 16:00"
        time_element = soup.select_one('div.pull-left.trailer.text-info')
        if time_element:
            time_text = time_element.get_text(strip=True)
            result['timestamp'] = time_text.replace("掛牌時間：", "").strip()

        if not result['passbook']['buy'] and not result['physical']['buy']:
            logger.warning("Parsed data is all None. HTML structure might have changed.")

        return result

    except Exception as e:
        logger.error(f"Failed to fetch gold price: {e}")
        return None

if __name__ == "__main__":
    # Test the function
    print(get_gold_price())
