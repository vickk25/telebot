import os
import logging
import asyncio
import random
import requests
from flask import Flask, request
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes
)

# 1. Logging Setup (Helps debug issues)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. Configuration
TOKEN = os.getenv("BOT_TOKEN", "8535828230:AAF71_itHUM4_SzdLXUdneTUCgm_Ba69444") 
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://telebot-sepia.vercel.app/")

app = Flask(__name__)

# 3. Bot Logic Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    # Persistent keyboard (at the bottom of chat)
    reply_keyboard = [
        ['/joke', '/cat'],
        ['/rps']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    await update.message.reply_html(
        f"Hi {user.mention_html()}! Choose a function 👇",
        reply_markup=markup,
    )

async def cat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends random cat image."""
    try:
        url = "https://api.thecatapi.com/v1/images/search"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        cat_image_url = data[0]["url"]

        # Handle both command calls and callback queries
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_photo(photo=cat_image_url)
        elif update.message:
            await update.message.reply_photo(photo=cat_image_url)
            
    except Exception as e:
        logger.error(f"Error fetching cat: {e}")
        text = "Sorry, couldn't find a cat right now."
        if update.callback_query:
            await update.callback_query.message.reply_text(text)
        else:
            await update.message.reply_text(text)

async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches a random joke setup."""
    try:
        url = "https://official-joke-api.appspot.com/random_joke"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        setup_text = data["setup"]
        punchline = data["punchline"]

        # Note: Callback data has a 64-byte limit. Long punchlines might fail here.
        # Ideally, store the ID and fetch later, but for simple bots, this works if short.
        keyboard = [[InlineKeyboardButton("Reveal", callback_data=f"joke_{punchline}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(setup_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error fetching joke: {e}")
        await update.message.reply_text("Failed to fetch a joke.")

async def joke_reveal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reveals the punchline."""
    query = update.callback_query
    await query.answer()
    
    # Extract punchline from callback_data (format: "joke_PUNCHLINE")
    punchline = query.data.split("joke_", 1)[1]
    await query.edit_message_text(punchline)

# --- Rock Paper Scissors Logic ---
def get_winner(user_choice: str, bot_choice: str) -> str:
    if user_choice == bot_choice:
        return "tie"
    if (
        (user_choice == "rock" and bot_choice == "scissors")
        or (user_choice == "paper" and bot_choice == "rock")
        or (user_choice == "scissors" and bot_choice == "paper")
    ):
        return "user"
    return "bot"

async def rps_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
            InlineKeyboardButton("📄 Paper", callback_data="rps_paper"),
        ],
        [InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👊 **Rock Paper Scissors** 👊\nChoose!",
        reply_markup=reply_markup
    )

async def rps_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_choice = query.data.split("_")[1]
    bot_choice = random.choice(["rock", "paper", "scissors"])
    winner = get_winner(user_choice, bot_choice)
    
    emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    
    result_text = "🤝 TIE!"
    if winner == "user":
        result_text = "🎉 YOU WIN!"
    elif winner == "bot":
        result_text = "😈 BOT WINS!"

    text = (
        f"{emojis[user_choice]} **You:** {user_choice.title()}\n"
        f"{emojis[bot_choice]} **Bot:** {bot_choice.title()}\n\n"
        f"{result_text}\n"
        f"🔄 Play again?"
    )
    
    # Re-use the same keyboard for replay
    keyboard = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
            InlineKeyboardButton("📄 Paper", callback_data="rps_paper"),
        ],
        [InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors")],
    ]

    await query.edit_message_text(
        text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
    )

# 4. Initialize Application
# We create a global bot app but initialize it inside the route for Vercel efficiency
bot_app = Application.builder().token(TOKEN).build()

# Add Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("cat", cat))
bot_app.add_handler(CallbackQueryHandler(cat, pattern="^cat_"))
bot_app.add_handler(CommandHandler("joke", joke))
bot_app.add_handler(CallbackQueryHandler(joke_reveal, pattern="^joke_"))
bot_app.add_handler(CommandHandler("rps", rps_start))
bot_app.add_handler(CallbackQueryHandler(rps_play, pattern="^rps_"))


# 5. Flask Routes (For Vercel/Webhooks)
@app.route('/', methods=['GET', 'POST'])
async def webhook():
    """Handle incoming Telegram updates via Webhook"""
    if request.method == "POST":
        await bot_app.initialize()
        # Decode the update
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        # Process the update
        await bot_app.process_update(update)
        # Shutdown to save resources in serverless environment
        await bot_app.shutdown()
        
        return "OK", 200
    return "Bot is running!", 200


# 6. Execution Logic
if __name__ == "__main__":
    # Local Development: Use Polling
    print("Starting bot in POLLING mode...")
    bot_app.run_polling()