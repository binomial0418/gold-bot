from flask import Flask, render_template, jsonify, request
import os
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging
import urllib.parse
import json
from scraper import get_gold_price
from analysis import get_market_trend
import datetime
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache for latest gold price
latest_price = {
    "passbook": {"buy": None, "sell": None},
    "physical": {"buy": None, "sell": None},
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
        # Fetch Trend Analysis
        try:
            trend_report = get_market_trend()
            price_data['trend'] = trend_report
        except Exception as e:
            logger.error(f"Failed to fetch trend: {e}")
            price_data['trend'] = "無法取得分析資料"

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
        phy_sell = data['physical'].get('sell', 'N/A')
        time_str = data.get('timestamp', datetime.datetime.now().strftime("%H:%M"))
        
        # Calculate 1 Mace (1/10 Tael) and 4.5 Taels price
        phy_buy_val = 0
        phy_buy_mace = 'N/A'
        phy_sell_mace = 'N/A'
        phy_buy_45 = 'N/A'
        
        try:
            if phy_buy and phy_buy != 'N/A':
                phy_buy_val = float(phy_buy.replace(',', ''))
                phy_buy_mace = "{:,.0f}".format(phy_buy_val / 10)
                phy_buy_45 = "{:,.0f}".format(phy_buy_val * 4.5)
            
            if phy_sell and phy_sell != 'N/A':
                phy_sell_val = float(phy_sell.replace(',', ''))
                phy_sell_mace = "{:,.0f}".format(phy_sell_val / 10)
        except ValueError:
            pass

        # Get Market Trend (from cached data)
        trend_report = data.get('trend', '分析資料未更新')

        msg = f"[台銀黃金報價] {time_str}\n存摺賣出: {pb_sell} | 回收: {pb_buy}\n實體賣出(1錢): {phy_sell_mace} | 回收: {phy_buy_mace}\n實體回收(4.5兩): {phy_buy_45}\n\n{trend_report}"
        
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
# Only start scheduler in the reloader process (if debugging) or main process (if not debugging)
if os.environ.get('FLASK_DEBUG') != '1' or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler = BackgroundScheduler()

    # 1. Automatic Fetch: Every 30 minutes (e.g. 09:00, 09:30...)
    scheduler.add_job(func=update_price_cache, trigger="cron", minute="0,30")

    # 2. Daily Notification: 08:00 AM
    scheduler.add_job(func=job_daily_notify, trigger="cron", hour=8, minute=0)

    # 3. Add immediate job (run now) to ensure data AND notification on startup
    scheduler.add_job(func=job_daily_notify, trigger="date", run_date=datetime.datetime.now())

    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
else:
    logger.info("Scheduler skipped in main process (waiting for reloader).")

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
