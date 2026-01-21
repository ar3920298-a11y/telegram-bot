import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8331060607:AAFZ8DE786GEWByeEC7pYnR_q8PXvODG6UA"
ADMIN_ID = 8591553697
QR_LINK = "https://instasize.com/p/c9ecaad2defe213cb86e9190cf7cc248f612dc555a6d4085f10c1f12e3e62fcd"

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
        [InlineKeyboardButton("₹4000", callback_data="buy_4000")]
    ]
    await update.message.reply_text(
        "Welcome! Choose amount:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    amount = query.data.split("_")[1]
    context.user_data["amount"] = amount

    await query.message.reply_photo(
        photo=QR_LINK,
        caption=f"Pay ₹{amount} using this QR.\n\nAfter payment, send your UTR."
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
            InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}")
        ]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"New Payment\nUser: {user_id}\nAmount: ₹{amount}\nUTR: {utr}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    action, user_id = query.data.split("_")

    if user_id not in pending:
        await query.message.reply_text("No pending request.")
        return

    amount = pending[user_id]["amount"]

    if action == "approve":
        if len(stock[amount]) == 0:
            await query.message.reply_text("❌ Out of stock. Please refill.")
            return

        code = stock[amount].pop(0)

        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"Payment approved ✅\nYour code: {code}"
        )

        del pending[user_id]
        save_data(data)

        await query.message.reply_text("Approved & code sent.")

    elif action == "reject":
        await context.bot.send_message(
            chat_id=int(user_id),
            text="Payment rejected ❌"
        )

        del pending[user_id]
        save_data(data)

        await query.message.reply_text("Rejected.")

async def addstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        amount = context.args[0]
        code = context.args[1]
    except:
        await update.message.reply_text("Usage: /addstock AMOUNT CODE")
        return

    if amount not in stock:
        await update.message.reply_text("Invalid amount.")
        return

    stock[amount].append(code)
    save_data(data)

    await update.message.reply_text(f"Added to ₹{amount} stock.")

async def view_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    text = "📦 Stock:\n"
    for amt in stock:
        text += f"₹{amt}: {len(stock[amt])}\n"

    await update.message.reply_text(text)

async def view_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not pending:
        await update.message.reply_text("No pending payments.")
        return

    text = "⏳ Pending:\n"
    for user in pending:
        text += f"User: {user} | ₹{pending[user]['amount']} | {pending[user]['utr']}\n"

    await update.message.reply_text(text)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buy_buttons, pattern="^buy_"))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^(approve|reject)_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, utr_handler))
app.add_handler(CommandHandler("addstock", addstock))
app.add_handler(CommandHandler("stock", view_stock))
app.add_handler(CommandHandler("pending", view_pending))

app.run_polling()
