from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging
import urllib.parse
import json
from scraper import get_gold_price
import datetime
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache for latest gold price
latest_price = {
    "passbook": {"buy": None, "sell": None},
    "physical": {"buy": None},
    "timestamp": None
}

def update_price_cache():
    """
    Fetches the latest gold price and updates the global cache.
    Returns the fetched data.
    """
    global latest_price
    logger.info("Starting job: update_price_cache")
    price_data = get_gold_price()
    
    if price_data:
        latest_price = price_data
        logger.info(f"Updated gold price: {latest_price}")
        return price_data
    else:
        logger.error("Failed to fetch gold price.")
        return None

def job_daily_notify():
    """
    Daily job to fetch latest price and send notification.
    Runs at 08:00 AM.
    """
    logger.info("Starting daily notification job.")
    # Force update first to ensure fresh data for notification
    data = update_price_cache()
    
    if data:
        notify_user(data)
    else:
        # If fetch failed, try to send notification with cached data or error
        logger.warning("Fetch failed during daily notify, using cached data if available.")
        if latest_price['timestamp']:
            notify_user(latest_price)

def notify_user(data):
    """
    Sends a notification to Synology Chat Webhook.
    """
    # Synology Chat Webhook URL
    webhook_url = 'https://nas.inskychen.com/webapi/entry.cgi?api=SYNO.Chat.External&method=incoming&version=2&token=%22SP2E3VZdLQdaPFP5hCVNDRSXgVzyZ1gsvotOEE587ETxCf2I44Kgv0NdrnZLkHrF%22'
    
    try:
        pb_sell = data['passbook'].get('sell', 'N/A')
        pb_buy = data['passbook'].get('buy', 'N/A')
        phy_buy = data['physical'].get('buy', 'N/A')
        time_str = data.get('timestamp', datetime.datetime.now().strftime("%H:%M"))
        
        # Calculate 4.5 Taels price
        phy_buy_val = 0
        phy_buy_45 = 'N/A'
        try:
            if phy_buy and phy_buy != 'N/A':
                # Remove commas if present
                phy_buy_val = float(phy_buy.replace(',', ''))
                phy_buy_45 = "{:,.0f}".format(phy_buy_val * 4.5)
        except ValueError:
            pass

        msg = f"[台銀黃金報價] {time_str}\n存摺賣出: {pb_sell}\n存摺回收: {pb_buy}\n實體回收(1兩): {phy_buy}\n實體回收(4.5兩): {phy_buy_45}"
        
        # Python Equivalent:
        # data={'payload': json_string} translates to application/x-www-form-urlencoded body "payload=..."
        payload_data = {'payload': json.dumps({'text': msg})}
        
        logger.info(f"Sending notification to Synology Chat...")
        
        try:
            response = requests.post(webhook_url, data=payload_data, timeout=10)
            if response.status_code == 200:
                logger.info("Notification sent successfully.")
            else:
                logger.error(f"Failed to send notification. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            logger.error(f"Failed to send notification request: {e}")
            
    except Exception as e:
        logger.error(f"Error constructing notification message: {e}")

# Setup Scheduler
scheduler = BackgroundScheduler()

# 1. Automatic Fetch: Every hour on the hour (e.g. 09:00, 10:00...)
scheduler.add_job(func=update_price_cache, trigger="cron", minute=0)

# 2. Daily Notification: 08:00 AM
# Note: Since we have an hourly fetch at 08:00 (minute=0), this might overlap.
# Ideally, we want to ensure the notify uses fresh data.
# The job_daily_notify calls update_price_cache internally. 
# To avoid double fetching at 08:00, we could exclude 08:00 from the hourly job or just let it happen (redundant but safe).
# Let's just execute notify job at 08:00, which updates data. 
# And hourly job runs at other times?
# Actually, calling update twice is fine, but better to be clean.
# Let's keep it simple: Hourly job runs every hour. Daily notify runs at 08:00 (maybe slightly after? or independently).
# User request: "早上八點發送通之前抓一次".
# So: 
# Hourly job: 0, 1, ... 7, 9, ... 23 ?
# Or just let them be independent.
# Let's set notify to run *also* at 08:00.
scheduler.add_job(func=job_daily_notify, trigger="cron", hour=8, minute=0)

# 3. Add immediate job (run now) to ensure data AND notification on startup
scheduler.add_job(func=job_daily_notify, trigger="date", run_date=datetime.datetime.now())

scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/gold')
def api_gold():
    # Support manual refresh via ?refresh=true
    if request.args.get('refresh') == 'true':
        logger.info("Manual refresh requested via API.")
        data = update_price_cache()
        if data:
            return jsonify(data)

    # If no data yet (e.g. just started), returns what we have
    global latest_price
    return jsonify(latest_price)

if __name__ == '__main__':
    # This block is NOT executed when running with `flask run`
    app.run(host='0.0.0.0', port=5001)
