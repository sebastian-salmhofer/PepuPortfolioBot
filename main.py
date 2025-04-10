import os
import re
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging to show debug output
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

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
    if not wallet.startswith("0x") or len(wallet) != 42:
        await update.message.reply_text("Invalid wallet address. Please try again.", parse_mode="HTML")
        return

    await update.message.reply_text("Fetching data, please wait...", parse_mode="HTML")

    try:
        api_url = API_URL + wallet
        logger.debug("Requesting URL: %s", api_url)
        # Increase timeout to 30 seconds for larger wallets
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()  # Raise an error for non-200 responses
        data = response.json()
        logger.debug("Received data: %s", data)

        # Build the summary message for the main portfolio data
        summary_msg = f"<b>Total Portfolio Value:</b> {format_usd(data.get('total_value_usd'))}\n\n"
        
        native = data.get("native_pepu", {})
        summary_msg += f"<b>Wallet PEPU</b>\n"
        summary_msg += f"Amount: {format_amount(native.get('amount'))}\n"
        summary_msg += f"Price: {format_price(native.get('price_usd'))}\n"
        summary_msg += f"Total: {format_usd(native.get('total_usd'))}\n\n"
        
        staked = data.get("staked_pepu", {})
        summary_msg += f"<b>Staked PEPU</b>\n"
        summary_msg += f"Amount: {format_amount(staked.get('amount'))}\n"
        summary_msg += f"Price: {format_price(staked.get('price_usd'))}\n"
        summary_msg += f"Total: {format_usd(staked.get('total_usd'))}\n\n"
        
        rewards = data.get("unclaimed_rewards", {})
        summary_msg += f"<b>Unclaimed Rewards</b>\n"
        summary_msg += f"Amount: {format_amount(rewards.get('amount'))}\n"
        summary_msg += f"Price: {format_price(rewards.get('price_usd'))}\n"
        summary_msg += f"Total: {format_usd(rewards.get('total_usd'))}\n\n"
        
        # Send the summary message
        await update.message.reply_text(summary_msg, parse_mode="HTML", disable_web_page_preview=True)
        
        # Process tokens: filter tokens with amount >= 1 and sort descending by total_usd
        tokens = [t for t in data.get("tokens", []) if t.get("amount", 0) >= 1]
        tokens = sorted(tokens, key=lambda t: float(t.get("total_usd", 0)), reverse=True)
        
        if tokens:
            chunk_size = 20  # 20 tokens per message
            for i in range(0, len(tokens), chunk_size):
                chunk = tokens[i:i+chunk_size]
                # Only add the header on the first chunk
                if i == 0:
                    tokens_msg = "<b>Other Tokens:</b>\n"
                else:
                    tokens_msg = ""
                for token in chunk:
                    token_link = f"https://www.geckoterminal.com/pepe-unchained/pools/{token.get('contract')}"
                    tokens_msg += f"<b><a href=\"{token_link}\">{token.get('name')} ({token.get('symbol')})</a></b>\n"
                    tokens_msg += f"Amount: {format_amount(token.get('amount'))}\n"
                    tokens_msg += f"Price: {format_price(token.get('price_usd'))}\n"
                    tokens_msg += f"Total: {format_usd(token.get('total_usd'))}\n"
                    if token.get("warning"):
                        warning_text = sanitize_html(token.get("warning"))
                        tokens_msg += f"<i>⚠ {warning_text}</i>\n"
                    tokens_msg += "\n"
                await update.message.reply_text(tokens_msg, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text("Error fetching data.", parse_mode="HTML")
        logger.error("Error fetching data: %s", e)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    user_last_wallet[user_id] = wallet
    await check_wallet(update, context, wallet)

def main():
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
