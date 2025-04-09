import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# In-memory store for user wallets
user_wallets = {}

API_URL = "https://pepu-portfolio-tracker.onrender.com/portfolio?wallet={}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the PEPU Portfolio Bot!\n"
        "To get started, send /portfolio followed by your wallet address like this:\n"
        "`/portfolio 0x123...`",
        parse_mode='Markdown'
    )

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a wallet address. Example: /portfolio 0x123...")
        return

    wallet = context.args[0]
    user_wallets[update.effective_user.id] = wallet
    await send_portfolio(update, context, wallet)

async def send_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet: str):
    response = requests.get(API_URL.format(wallet))
    if response.status_code != 200:
        await update.message.reply_text("Error fetching portfolio. Try again later.")
        return

    data = response.json()
    lines = [
        f"\n*Total Portfolio Value:* ${data['total_value_usd']:,}",
        f"\n*Wallet PEPU:* {data['native_pepu']['amount']:.4f} (${data['native_pepu']['total_usd']:.2f})",
        f"*Staked PEPU:* {data['staked_pepu']['amount']:.4f} (${data['staked_pepu']['total_usd']:.2f})",
        f"*Unclaimed Rewards:* {data['unclaimed_rewards']['amount']:.4f} (${data['unclaimed_rewards']['total_usd']:.2f})",
    ]

    if data["tokens"]:
        lines.append("\n*Other Tokens:*")
        for token in data["tokens"][:10]:  # limit to first 10
            lines.append(f"- {token['symbol']}: {token['amount']:.4f} (${token['total_usd']:.2f})")

    keyboard = [
        [InlineKeyboardButton("Check Another Wallet", callback_data="new_wallet")]
    ]

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "new_wallet":
        await query.edit_message_text(
            "Please send a new wallet address using /portfolio 0x..."
        )

app = ApplicationBuilder().token("YOUR_BOT_TOKEN_HERE").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("portfolio", portfolio))
app.add_handler(CallbackQueryHandler(button))

if __name__ == "__main__":
    app.run_polling()