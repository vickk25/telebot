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
from telegram.constants import ParseMode
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
# Try to get TOKEN from Environment Variable, fallback to your string for local testing if needed
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
        ['/rps', '/math']
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

        if update.message:
            await update.message.reply_photo(photo=cat_image_url)
            
    except Exception as e:
        logger.error(f"Error fetching cat: {e}")
        if update.message:
            await update.message.reply_text("Sorry, couldn't find a cat right now.")

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

# --- Math Battle Logic ---
async def generate_math_problem():
    """Helper to generate question and keyboard."""
    ops = ['+', '-', '*']
    op = random.choice(ops)
    
    if op == '*':
        a = random.randint(2, 12)
        b = random.randint(2, 12)
    else:
        a = random.randint(1, 50)
        b = random.randint(1, 50)
        
    question = f"{a} {op} {b}"
    answer = eval(question)
    
    choices = {answer}
    while len(choices) < 4:
        offset = random.randint(-10, 10)
        if offset != 0:
            choices.add(answer + offset)
    
    choices_list = list(choices)
    random.shuffle(choices_list)
    
    keyboard = [
        [
            InlineKeyboardButton(str(choices_list[0]), callback_data=f"math_ans_{choices_list[0]}_{answer}"),
            InlineKeyboardButton(str(choices_list[1]), callback_data=f"math_ans_{choices_list[1]}_{answer}")
        ],
        [
            InlineKeyboardButton(str(choices_list[2]), callback_data=f"math_ans_{choices_list[2]}_{answer}"),
            InlineKeyboardButton(str(choices_list[3]), callback_data=f"math_ans_{choices_list[3]}_{answer}")
        ]
    ]
    return f"🧠 **Math Battle** 🧠\n\nSolve this:\n`{question} = ?`", InlineKeyboardMarkup(keyboard)

async def math_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates a math problem and 4 options."""
    text, reply_markup = await generate_math_problem()
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
        )

async def math_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks the answer. If correct, immediately gives a new question."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    selected = int(data[2])
    actual = int(data[3])
    
    if selected == actual:
        # Correct! Generate new question immediately for continuous play
        text, reply_markup = await generate_math_problem()
        # Add a small success indicator to the top of the next question
        new_text = f"✅ **Correct!**\n\n{text}"
        await query.edit_message_text(
            new_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Wrong! End the streak and show play again button
        result_text = f"❌ **Wrong!**\nYou chose {selected}. The answer was {actual}."
        keyboard = [[InlineKeyboardButton("🔄 Try Again", callback_data="math_start")]]
        
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

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

async def dice_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rolls a 6-sided die."""
    result = random.randint(1, 6)
    keyboard = [[InlineKeyboardButton("Roll Again 🎲", callback_data="dice_roll")]]
    await update.message.reply_text(f"🎲 You rolled a {result}!", reply_markup=InlineKeyboardMarkup(keyboard))



# 4. Initialize Application
bot_app = Application.builder().token(TOKEN).build()

# Add Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("cat", cat))
bot_app.add_handler(CommandHandler("joke", joke))
bot_app.add_handler(CallbackQueryHandler(joke_reveal, pattern="^joke_"))
bot_app.add_handler(CommandHandler("math", math_start))
bot_app.add_handler(CallbackQueryHandler(math_start, pattern="^math_start$"))
bot_app.add_handler(CallbackQueryHandler(math_check, pattern="^math_ans_"))
bot_app.add_handler(CommandHandler("rps", rps_start))
bot_app.add_handler(CallbackQueryHandler(rps_play, pattern="^rps_"))
bot_app.add_handler(CommandHandler("dice", dice_roll))
bot_app.add_handler(CallbackQueryHandler(dice_roll, pattern="^roll_dice$"))


# 5. Flask Routes (For Vercel/Webhooks)
@app.route('/', methods=['GET', 'POST'])
async def webhook():
    """Handle incoming Telegram updates via Webhook"""
    if request.method == "POST":
        await bot_app.initialize()
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        await bot_app.process_update(update)
        await bot_app.shutdown()
        
        return "OK", 200
    return "Bot is running!", 200


# 6. Execution Logic
if __name__ == "__main__":
    # Local Development: Use Polling
    print("Starting bot in POLLING mode...")
    bot_app.run_polling()