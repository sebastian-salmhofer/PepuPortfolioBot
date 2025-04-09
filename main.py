import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# In-memory cache for user's last wallet address
user_last_wallet = {}

# Your API endpoint
API_URL = "https://pepu-portfolio-tracker.onrender.com/portfolio?wallet="

# --- Helper functions to format numbers ---
def format_amount(n):
    val = float(n)
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

# --- Functions to render each card ---
def render_card(label, item):
    # Use the key "icon" or fallback to "icon_url"
    icon = item.get("icon") or item.get("icon_url")
    out = f"<b>{label}</b>\n"
    if icon:
        out += f"Icon: <a href=\"{icon}\">View</a>\n"
    out += f"Amount: {format_amount(item['amount'])}\n"
    out += f"Price: {format_price(item['price_usd'])}\n"
    out += f"Total: {format_usd(item['total_usd'])}\n\n"
    return out

# --- Telegram Bot Handlers ---
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
        response = requests.get(API_URL + wallet)
        data = response.json()

        # Build the HTML message
        msg = f"<b>Total Portfolio Value:</b> {format_usd(data['total_value_usd'])}\n\n"
        msg += render_card("Wallet PEPU", data["native_pepu"])
        msg += render_card("Staked PEPU", data["staked_pepu"])
        msg += render_card("Unclaimed Rewards", data["unclaimed_rewards"])

        # Render other tokens if present
        if data.get("tokens"):
            msg += "<b>Other Tokens:</b>\n"
            for token in data["tokens"]:
                # Skip tokens with insignificant amounts
                if token["amount"] < 1:
                    continue
                token_link = f"https://www.geckoterminal.com/pepe-unchained/pools/{token['contract']}"
                msg += f"<b><a href=\"{token_link}\">{token['name']} ({token['symbol']})</a></b>\n"
                icon = token.get("icon_url")
                if icon:
                    msg += f"Icon: <a href=\"{icon}\">View</a>\n"
                msg += f"Amount: {format_amount(token['amount'])}\n"
                msg += f"Price: {format_price(token['price_usd'])}\n"
                msg += f"Total: {format_usd(token['total_usd'])}\n"
                if token.get("warning"):
                    msg += f"<i><font color=\"red\">⚠ {token['warning']}</font></i>\n"
                msg += "\n"

        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e
