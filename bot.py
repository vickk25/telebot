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
        ['/joke', '/cat', '/uno'],
        ['/rps', '/math', '/dice']
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
    keyboard = [[InlineKeyboardButton("Roll Again 🎲", callback_data="roll_dice")]]
    await update.message.reply_text(f"🎲 You rolled a {result}!", reply_markup=InlineKeyboardMarkup(keyboard))

async def dice_roll_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for rolling dice again."""
    query = update.callback_query
    await query.answer()
    result = random.randint(1, 6)
    keyboard = [[InlineKeyboardButton("Roll Again 🎲", callback_data="roll_dice")]]
    await query.edit_message_text(f"🎲 You rolled a {result}!", reply_markup=InlineKeyboardMarkup(keyboard))

COLORS = ['🔴', '🟡', '🟢', '🔵']
VALUES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'Skip', 'Draw2']

def create_deck():
    return [{"color": c, "value": v} for c in COLORS for v in VALUES]

def can_play(card, top_card):
    return card['color'] == top_card['color'] or card['value'] == top_card['value']

# --- HANDLERS ---
async def start_uno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts a new UNO game vs a Bot."""
    deck = create_deck()
    random.shuffle(deck)
    
    # Initial Deal
    user_hand = [deck.pop() for _ in range(7)]
    bot_hand = [deck.pop() for _ in range(7)]
    discard_pile = [deck.pop()]
    
    # Save game state in user_data
    context.user_data['uno'] = {
        'deck': deck,
        'user_hand': user_hand,
        'bot_hand': bot_hand,
        'discard': discard_pile
    }
    
    await send_uno_board(update, context)

async def send_uno_board(update, context, text_prefix=""):
    """Renders the current game state and the user's hand."""
    game = context.user_data['uno']
    top_card = game['discard'][-1]
    
    text = (
        f"{text_prefix}\n"
        f"🤖 Bot Cards: {len(game['bot_hand'])}\n"
        f"🃏 Top Card: **{top_card['color']} {top_card['value']}**\n"
        f"--- --- --- ---\n"
        f"Your Turn! Pick a card to play:"
    )
    
    # Build the player's hand as buttons
    keyboard = []
    row = []
    for i, card in enumerate(game['user_hand']):
        row.append(InlineKeyboardButton(f"{card['color']}{card['value']}", callback_data=f"uno_p_{i}"))
        if len(row) == 3: # 3 cards per row
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    
    # Add a Draw button
    keyboard.append([InlineKeyboardButton("📥 Draw a Card", callback_data="uno_draw")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def uno_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    game = context.user_data.get('uno')
    
    if not game:
        await query.answer("No active game. Start with /uno")
        return

    await query.answer()

    # --- PLAYER PLAYING A CARD ---
    if data.startswith("uno_p_"):
        idx = int(data.split("_")[-1])
        selected_card = game['user_hand'][idx]
        top_card = game['discard'][-1]

        if can_play(selected_card, top_card):
            game['discard'].append(game['user_hand'].pop(idx))
            
            if not game['user_hand']:
                await query.edit_message_text("🎉 **YOU WIN!** You played your last card.", parse_mode="Markdown")
                context.user_data['uno'] = None
                return
            
            await bot_turn(update, context)
        else:
            await query.answer("❌ That card doesn't match!", show_alert=True)

    # --- PLAYER DRAWING A CARD ---
    elif data == "uno_draw":
        if game['deck']:
            game['user_hand'].append(game['deck'].pop())
            await bot_turn(update, context)
        else:
            await query.answer("Deck is empty!")

async def bot_turn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The Bot's logic: Play the first matching card it finds."""
    game = context.user_data['uno']
    top_card = game['discard'][-1]
    
    # Visual delay so the user can see what's happening
    await update.callback_query.edit_message_text("🤖 Bot is thinking...")
    await asyncio.sleep(1.5)

    played = False
    for i, card in enumerate(game['bot_hand']):
        if can_play(card, top_card):
            game['discard'].append(game['bot_hand'].pop(i))
            bot_msg = f"🤖 Bot played {card['color']} {card['value']}!"
            played = True
            break
    
    if not played:
        if game['deck']:
            game['bot_hand'].append(game['deck'].pop())
            bot_msg = "🤖 Bot had no match and drew a card."
        else:
            bot_msg = "🤖 Bot had no match (Deck empty)."

    if not game['bot_hand']:
        await update.callback_query.edit_message_text("💀 **BOT WINS!** Better luck next time.", parse_mode="Markdown")
        context.user_data['uno'] = None
    else:
        await send_uno_board(update, context, text_prefix=bot_msg)


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
bot_app.add_handler(CallbackQueryHandler(dice_roll_callback, pattern="^roll_dice$"))    
bot_app.add_handler(CommandHandler("uno", start_uno))
bot_app.add_handler(CallbackQueryHandler(uno_callback, pattern="^uno_"))

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