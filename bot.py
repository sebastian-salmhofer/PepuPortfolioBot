import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import requests

API_URL = os.getenv("API_URL", "https://pepu-portfolio-tracker.onrender.com")
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

user_last_wallet = {}

def format_amount(n):
    n = float(n)
    if n >= 1e9:
        return f"{n / 1e9:.2f}B"
    elif n >= 1e6:
        return f"{n / 1e6:.2f}M"
    elif n >= 1e3:
        return f"{n / 1e3:.2f}K"
    return f"{n:.4f}"

def format_usd(n):
    return f"${float(n):,.2f}"

def render_portfolio(data):
    lines = [f"*Total Value:* {format_usd(data['total_value_usd'])}"]
    lines.append("")

    def token_line(label, token):
        return f"*{label}*\nAmount: {format_amount(token['amount'])} | Value: {format_usd(token['total_usd'])}"

    lines.append(token_line("Wallet PEPU", data["native_pepu"]))
    lines.append(token_line("Staked PEPU", data["staked_pepu"]))
    lines.append(token_line("Unclaimed Rewards", data["unclaimed_rewards"]))
    lines.append("")

    if data["tokens"]:
        lines.append("*Other Tokens:*")
        for token in data["tokens"]:
            if token["amount"] < 1:
                continue
            lines.append(f"{token['name']} ({token['symbol']})\nAmount: {format_amount(token['amount'])} | Value: {format_usd(token['total_usd'])}")
    else:
        lines.append("_No other tokens found._")

    return "\n\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [[InlineKeyboardButton("Check another wallet", callback_data="check_other")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if user_id in user_last_wallet:
        wallet = user_last_wallet[user_id]
        await update.message.reply_text(f"Fetching portfolio for `{wallet}`...", parse_mode="Markdown")
        try:
            res = requests.get(f"{API_URL}/portfolio?wallet={wallet}")
            data = res.json()
            msg = render_portfolio(data)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        except:
            await update.message.reply_text("Failed to fetch data.")
    else:
        await update.message.reply_text("Welcome! Please send a wallet address to get started.")

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text.strip()
    if not wallet.startswith("0x") or len(wallet) != 42:
        await update.message.reply_text("Invalid wallet address. Please try again.")
        return

    user_id = update.effective_user.id
    user_last_wallet[user_id] = wallet

    await update.message.reply_text(f"Fetching portfolio for `{wallet}`...", parse_mode="Markdown")

    try:
        res = requests.get(f"{API_URL}/portfolio?wallet={wallet}")
        data = res.json()
        msg = render_portfolio(data)
        keyboard = [[InlineKeyboardButton("Check another wallet", callback_data="check_other")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    except:
        await update.message.reply_text("Failed to fetch data.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_other":
        await query.edit_message_text("Please send the new wallet address.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_wallet))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
