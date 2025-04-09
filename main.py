import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_BASE_URL = "https://pepu-portfolio-tracker.onrender.com/portfolio?wallet="
user_last_wallet = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_last_wallet:
        await update.message.reply_text(
            f"Welcome back! Checking last wallet: {user_last_wallet[user_id]}...
"
            f"Type /wallet <address> to check another one."
        )
        await fetch_portfolio(update, context, user_last_wallet[user_id])
    else:
        await update.message.reply_text("Welcome! Send a wallet address with /wallet <address> to get started.")

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Please provide a wallet address like this:\n/wallet 0x123...")
        return

    address = context.args[0]
    if not address.startswith("0x") or len(address) != 42:
        await update.message.reply_text("That doesn't look like a valid wallet address.")
        return

    user_last_wallet[update.effective_user.id] = address
    await fetch_portfolio(update, context, address)

async def fetch_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE, address: str):
    await update.message.reply_text("Fetching portfolio, please wait...")
    try:
        res = requests.get(API_BASE_URL + address)
        data = res.json()

        total = data.get("total_value_usd", 0)
        msg = f"Total Portfolio Value: ${total:,.2f}\n"

        def token_line(label, item):
            amt = item['amount']
            price = item['price_usd']
            value = item['total_usd']
            return f"{label}:\n  Amount: {amt:,.4f}\n  Price: ${price:.6f}\n  Total: ${value:,.2f}\n"

        msg += token_line("Wallet PEPU", data["native_pepu"])
        msg += token_line("Staked PEPU", data["staked_pepu"])
        msg += token_line("Unclaimed Rewards", data["unclaimed_rewards"])

        await update.message.reply_text(msg)
    except Exception as e:
        print("Error:", e)
        await update.message.reply_text("Failed to fetch portfolio. Please try again later.")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", wallet))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()