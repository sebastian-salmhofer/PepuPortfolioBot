import os
import re
import requests
import random
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging to show errors only
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.ERROR
)
logger = logging.getLogger(__name__)

portfolio_request_count = 0
next_ad_trigger = random.randint(3, 5)

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

footer_text = "<b>Check out your portfolio on the web + explore exclusive merch</b> 🛍️\n🔗 pepe-bitcoin.com"
user_last_wallet = {}

API_URL = "https://pepu-portfolio-tracker.onrender.com/portfolio?wallet="

def sanitize_html(text):
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

def extract_symbols(lp_name):
    match = re.search(r'- ([^/-]+)/([^ -]+)', lp_name)
    if match:
        return match.group(1), match.group(2)
    return "?", "?"

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

    portfolio_request_count += 1
    if portfolio_request_count >= next_ad_trigger:
        ad_message = random.choice(ad_messages)
        await update.message.reply_text(ad_message, parse_mode="HTML", disable_web_page_preview=True)
        portfolio_request_count = 0
        next_ad_trigger = random.randint(3, 5)

    try:
        api_url = API_URL + wallet
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()

        summary_msg = "🐸 <b>PepeBitcoin's PEPU Portfolio Tracker</b> 🐸\n\n"
        summary_msg += f"<b>Total Portfolio Value:</b> {format_usd(data.get('total_value_usd'))}\n\n"
        
        native = data.get("native_pepu", {})
        summary_msg += f"<b>Wallet PEPU</b>\nAmount: {format_amount(native.get('amount'))}\n"
        summary_msg += f"Price: {format_price(native.get('price_usd'))}\nTotal: {format_usd(native.get('total_usd'))}\n\n"
        
        staked = data.get("staked_pepu", {})
        summary_msg += f"<b>Staked PEPU</b>\nAmount: {format_amount(staked.get('amount'))}\n"
        summary_msg += f"Price: {format_price(staked.get('price_usd'))}\nTotal: {format_usd(staked.get('total_usd'))}\n\n"
        
        rewards = data.get("unclaimed_rewards", {})
        summary_msg += f"<b>Unclaimed Rewards</b>\nAmount: {format_amount(rewards.get('amount'))}\n"
        summary_msg += f"Price: {format_price(rewards.get('price_usd'))}\nTotal: {format_usd(rewards.get('total_usd'))}\n\n"

        await update.message.reply_text(summary_msg, parse_mode="HTML", disable_web_page_preview=True)

        # Tokens
        tokens = [
            t for t in data.get("tokens", [])
            if t.get("amount", 0) >= 1 and (
                float(t.get("total_usd", 0)) >= 0.01 or 
                (t.get("warning") and "Error fetching price data" in t.get("warning"))
            )
        ]
        tokens = sorted(tokens, key=lambda t: float(t.get("total_usd", 0)), reverse=True)

        if tokens:
            chunk_size = 20
            for i in range(0, len(tokens), chunk_size):
                chunk = tokens[i:i+chunk_size]
                tokens_msg = "<b>Other Tokens:</b>\n" if i == 0 else ""
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
                if i + chunk_size >= len(tokens) and not data.get("lp_positions"):
                    tokens_msg += footer_text
                await update.message.reply_text(tokens_msg, parse_mode="HTML", disable_web_page_preview=True)

        # LP Positions
        lp_positions = data.get("lp_positions", [])
        if lp_positions:
            lp_msg = "<b>Liquidity Pool Positions:</b>\n"
            for lp in lp_positions:
                symbol0, symbol1 = extract_symbols(lp.get("lp_name", ""))
                lp_msg += f"\n<b>{lp.get('lp_name')}</b>\n"
                lp_msg += f"{symbol0}: {format_amount(lp.get('amount0'))}\n"
                lp_msg += f"{symbol1}: {format_amount(lp.get('amount1'))}\n"
                total = lp.get("amount0_usd", 0) + lp.get("amount1_usd", 0)
                lp_msg += f"<b>Total:</b> {format_usd(total)}\n"
                if lp.get("warning"):
                    lp_msg += f"<i>⚠ {sanitize_html(lp['warning'])}</i>\n"
            lp_msg += "\n" + footer_text
            await update.message.reply_text(lp_msg, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        await update.message.reply_text("Error fetching data.", parse_mode="HTML")
        logger.error("Error fetching data: %s", e)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_last_wallet
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
