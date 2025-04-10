import os
import re
import requests
import random
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging to show debug output
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Global variables for ad triggering
portfolio_request_count = 0
next_ad_trigger = random.randint(3, 5)

# Advertisement messages (HTML formatted; bold part as specified)
ad_messages = [
    "<b>🛒 Real holders rock the merch.</b>\nSupport the project & rep PBTC in style:\n🔗 pepe-bitcoin.com/store",
    "<b>🔥 You checked your portfolio. Now dress like a degen.</b>\nPBTC merch store open 24/7 👕\n🔗 pepe-bitcoin.com/store",
    "<b>💚 Your bags look good. You should too.</b>\nGrab some PBTC gear:\n🔗 pepe-bitcoin.com/store",
    "<b>🎯 Tracking your bags is smart. Shilling them is smarter.</b>\nPBTC merch now live:\n🔗 pepe-bitcoin.com/store",
    "<b>👀 Pepe’s watching your bags grow...</b>\nLet the world know you're early.\n🛍️ pepe-bitcoin.com/store",
    "<b>⚡ You don’t need a bull run to wear a hoodie like a legend.</b>\nPBTC merch available now.\n🔗 pepe-bitcoin.com/store",
    "<b>🐸 This ain’t just a meme — it’s a movement.</b>\nShow some love with PBTC merch:\n🔗 pepe-bitcoin.com/store",
    "<b>💼 Bags stacked. Mission clear. Merch acquired?</b>\nRep PBTC everywhere:\n🔗 pepe-bitcoin.com/store",
    "<b>🚀 PBTC isn't just a coin. It's a culture.</b>\nJoin the movement:\n🛍️ pepe-bitcoin.com/store",
    "<b>👕 From chart watchers to merch rockers — all PBTC holders welcome.</b>\nPepeBitcoin merch store:\n🔗 pepe-bitcoin.com/store"
]

# Footer text to add on the last tokens message
footer_text = "<b>Check out your portfolio on the web + explore exclusive merch</b> 🛍️\n🔗 pepe-bitcoin.com"

# In-memory cache for user's last wallet address
user_last_wallet = {}

# Your API endpoint
API_URL = "https://pepu-portfolio-tracker.onrender.com/portfolio?wallet="

def sanitize_html(text):
    """
    Remove unsupported HTML tags (e.g. <font>) from text.
    """
    if not text:
        return text
    return re.sub(r'</?font[^>]*>', '', text)

def format_amount(n):
    try:
        val = float(n)
    except (ValueError, TypeError):
        return "N/A"
    if val >= 1e9:
        return f"{val/1e9:.2f}B"
    elif val >= 1e6:
        return f"{val/1e6:.2f}M"
    elif val >= 1e3:
        return f"{val/1e3:.2f}K"
    return f"{val:,.4f}"

def format_usd(n):
    try:
        return f"${float(n):,.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_price(n):
    try:
        return f"${float(n):,.6f}"
    except (ValueError, TypeError):
        return "N/A"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_last_wallet:
        await update.message.reply_text(
            f"Welcome back! Checking last wallet: {user_last_wallet[user_id]}...",
            parse_mode="HTML"
        )
        await check_wallet(update, context, user_last_wallet[user_id])
    else:
        await update.message.reply_text(
            "Welcome to the Pepu Portfolio Bot!\nPlease enter a wallet address (0x...)",
            parse_mode="HTML"
        )

async def check_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet: str):
    global portfolio_request_count, next_ad_trigger
    if not wallet.startswith("0x") or len(wallet) != 42:
        await update.message.reply_text("Invalid wallet address. Please try again.", parse_mode="HTML")
        return

    await update.message.reply_text("Fetching data, please wait...", parse_mode="HTML")

    # Increment and possibly send an ad message every 3-5 portfolio requests
    portfolio_request_count += 1
    if portfolio_request_count >= next_ad_trigger:
        ad_message = random.choice(ad_messages)
        await update.message.reply_text(ad_message, parse_mode="HTML", disable_web_page_preview=True)
        portfolio_request_count = 0
        next_ad_trigger = random.randint(3, 5)

    try:
        api_url = API_URL + wallet
        logger.debug("Requesting URL: %s", api_url)
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.debug("Received data: %s", data)

        # Build the summary message for the main portfolio data
        summary_msg = f"<b>Total Portfolio Value:</_
