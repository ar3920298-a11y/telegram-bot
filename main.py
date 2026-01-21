import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
QR_LINK = os.getenv("QR_LINK")

DATA_FILE = "data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "stock": {"500": [], "1000": [], "2000": [], "4000": []},
        "pending": {}
    }


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


data = load_data()
stock = data["stock"]
pending = data["pending"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("₹500", callback_data="buy_500")],
        [InlineKeyboardButton("₹1000", callback_data="buy_1000")],
        [InlineKeyboardButton("₹2000", callback_data="buy_2000")],
        [InlineKeyboardButton("₹4000", callback_data="buy_4000")],
    ]
    await update.message.reply_text(
        "Welcome! Choose amount:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def buy_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    amount = query.data.split("_")[1]
    context.user_data["amount"] = amount

    await query.message.reply_photo(
        photo=QR_LINK,
        caption=f"Pay ₹{amount} using this QR.\nAfter payment, send your UTR number."
    )


async def utr_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    utr = update.message.text
    amount = context.user_data.get("amount")

    if not amount:
        return

    pending[user_id] = {
        "utr": utr,
        "amount": amount
    }

    save_data(data)

    await update.message.reply_text("Payment submitted. Waiting for admin approval.")

    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}"),
        ]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"New Payment\nUser: {user_id}\nAmount: ₹{amount}\nUTR: {utr}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("_")

    if user_id not in pending:
        await query.message.reply_text("Request not found.")
        return

    user_data = pending[user_id]
    amount = user_data["amount"]

    if action == "approve":
        if stock[amount]:
            code = stock[amount].pop(0)
            await context.bot.send_message(chat_id=user_id, text=f"Your code: {code}")
        else:
            await context.bot.send_message(chat_id=user_id, text="Out of stock. Please wait.")
    else:
        await context.bot.send_message(chat_id=user_id, text="Payment rejected.")

    del pending[user_id]
    save_data(data)

    await query.message.reply_text("Action completed.")


async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buy_buttons, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|reject)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, utr_handler))

    print("Bot is running...")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
