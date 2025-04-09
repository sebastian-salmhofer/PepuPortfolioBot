import os
import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Get bot token from environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Store user wallet state in memory
user_last_wallet = {}

# API endpoint
API_URL = "https://pepu-portfolio-tracker.onrender.com/portfolio?wallet="

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_last_wallet:
        await update.message.reply_text(
            f"Welcome back! Checking last wallet: {user_last_wallet[user_id]}..."
        )
        await check_wallet(update, context, user_last_wallet[user_id])
    else:
        await update.message.reply_text(
            "Welcome to the Pepu Portfolio Bot!\nPlease enter a wallet address (0x...)."
        )

async def check_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet: str):
    if not wallet.startswith("0x") or len(wallet) != 42:
        await update.message.reply_text("Invalid wallet address. Please try again.")
        return

    await update.message.reply_text("Fetching data, please wait...")

    try:
        response = requests.get(API_URL + wallet)
        data = response.json()

        msg = f"Total Portfolio Value: ${data['total_value_usd']}\n\n"

        def section(label, item):
            return (
                f"{label}\n"
                f"- Amount: {round(item['amount'], 4)}\n"
                f"- Value: ${round(item['total_usd'], 2)}\n\n"
            )

        msg += section("Wallet PEPU", data["native_pepu"])
        msg += section("Staked PEPU", data["staked_pepu"])
        msg += section("Unclaimed Rewards", data["unclaimed_rewards"])

        tokens = data["tokens"]
        if tokens:
            msg += "Other Tokens:\n"
            for t in tokens:
                if t["amount"] < 1:
                    continue
                msg += f"- {t['name']} ({t['symbol']}): ${round(t['total_usd'], 2)}\n"

        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text("Error fetching data.")
        print(e)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    user_last_wallet[user_id] = wallet
    await check_wallet(update, context, wallet)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Delete any previously set webhook to avoid conflict.
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("Deleted webhook. Starting polling...")
    
    await app.run_polling()

if __name__ == "__main__":
    # Instead of asyncio.run() (which complains if an event loop is already running)
    # we get the running loop, schedule our main task, and call run_forever().
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
