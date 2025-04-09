
import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

API_URL = "https://pepu-portfolio-tracker.onrender.com/portfolio?wallet="
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

user_wallets = {}  # Maps user_id to last used wallet

def format_amount(n):
    n = float(n)
    if n >= 1e9:
        return f"{n / 1e9:.2f}B"
    elif n >= 1e6:
        return f"{n / 1e6:.2f}M"
    elif n >= 1e3:
        return f"{n / 1e3:.2f}K"
    return f"{n:.2f}"

def format_usd(n):
    return f"${float(n):,.2f}" if n else "N/A"

def format_price(p):
    return f"${float(p):,.6f}" if p else "N/A"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Pepu Portfolio Bot! Send /portfolio followed by your wallet address to get started.")

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a wallet address like this:
/portfolio 0xYourWallet")
        return

    wallet = context.args[0].strip()
    if not wallet.startswith("0x") or len(wallet) != 42:
        await update.message.reply_text("Invalid wallet address. It should start with 0x and be 42 characters long.")
        return

    user_wallets[update.effective_user.id] = wallet
    await send_portfolio(update, context, wallet)

async def send_portfolio(update, context, wallet):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = requests.get(API_URL + wallet).json()
        message = f"*Total Portfolio Value:* {format_usd(response['total_value_usd'])}\n\n"

        def render_card(label, item):
            return f"*{label}*\nAmount: {format_amount(item['amount'])}\nPrice: {format_price(item['price_usd'])}\nTotal: {format_usd(item['total_usd'])}\n"

        message += render_card("Wallet PEPU", response["native_pepu"]) + "\n"
        message += render_card("Staked PEPU", response["staked_pepu"]) + "\n"
        message += render_card("Unclaimed Rewards", response["unclaimed_rewards"]) + "\n"

        message += "\n*Other Tokens:*\n"
        token_lines = []
        for token in response["tokens"]:
            if float(token["amount"]) >= 1:
                token_lines.append(f"{token['symbol']}: {format_amount(token['amount'])} = {format_usd(token['total_usd'])}")
        message += "\n".join(token_lines) if token_lines else "No significant balances."

        keyboard = [
            [InlineKeyboardButton("Check Another", callback_data="check_another")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("Failed to load portfolio. Try again later.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check_another":
        await query.edit_message_text("Send /portfolio followed by a wallet address.")

def main():
    if not BOT_TOKEN:
        raise Exception("TELEGRAM_BOT_TOKEN environment variable not set")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("portfolio", portfolio))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == "__main__":
    main()
