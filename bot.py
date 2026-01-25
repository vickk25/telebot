#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import asyncio


import requests
import logging

from telegram import *
from telegram.ext import *
from random import *
import random
import flask


app = flask.Flask(__name__)

WEBHOOK_URL = 'https://telebot-sepia.vercel.app/'
TOKEN = "8227179644:AAGd2SegWXWiMZ0KlYKhYtI5npopw6n12Vs"

telebot = (
    Application.builder()
    .token(TOKEN)
    .build()
)



# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    # # menu = [
    # #     [InlineKeyboardButton("Random Cat image", callback_data='cat')],
    # #     [InlineKeyboardButton("Random Joke", callback_data="joke")],
    # #     [InlineKeyboardButton("Rock Paper Scissors", callback_data="rps")]
    #     ]
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Choose a function:",
        # reply_markup= InlineKeyboardMarkup(menu)
        reply_markup=ForceReply(selective=True),
    )

    # async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #     query = update.callback_query
    #     await query.answer()

    #     if query.data == 'cat':
    #         await query.edit_message_media(f'Here is a random cat image: {cat}')

    #     elif query.data == 'joke':
    #         await query.edit_message_text(f'Here is a random joke: {joke}')

    #     elif query.data == 'rps':
    #         await query.edit_message_text({rps_play})

    # async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    # await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


async def cat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends random cat image."""
    url = "https://api.thecatapi.com/v1/images/search"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    cat_image_url = data[0]["url"]

    await update.message.reply_photo(photo=cat_image_url)


async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = "https://official-joke-api.appspot.com/random_joke"

    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    message = data["setup"]
    keyboard = [
        [InlineKeyboardButton("Reveal", callback_data=f"joke_{data['punchline']}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, reply_markup=reply_markup)


async def joke_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    punchline = query.data
    await query.edit_message_text(punchline.strip("joke_"))


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
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def rps_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    EMOJIS = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    query = update.callback_query
    await query.answer()

    user_choice = query.data.split("_")[1]
    bot_choice = random.choice(["rock", "paper", "scissors"])
    winner = get_winner(user_choice, bot_choice)

    if winner == "user":
        result = "🎉 YOU WIN!"
    elif winner == "bot":
        result = "😈 BOT WINS!"
    else:
        result = "🤝 TIE!"
    text = (
        f"{EMOJIS[user_choice]} **You:** {user_choice.title()}\n"
        f"{EMOJIS[bot_choice]} **Bot:** {bot_choice.title()}\n\n"
        f"{result}\n"
        f"🔄 Play again?"
    )
    keyboard = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
            InlineKeyboardButton("📄 Paper", callback_data="rps_paper"),
        ],
        [InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors")],
    ]

    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

@app.route('/', methods=['GET', 'POST'])
async def webhook():
    """Handle incoming Telegram updates"""

    telebot.add_handler(CommandHandler("start", start))
    if flask.request.method == "POST":
        await telebot.initialize()
        update = Update.de_json(flask.request.get_json(force=True), telebot.bot)
        await telebot.process_update(update)

        return "OK", 200
    else:
        return "Hello", 200

async def setup_webhook():
    """Set the webhook with Telegram on startup"""
    async with telebot:
        await telebot.bot.set_webhook(url=WEBHOOK_URL)
        print(f"Webhook set to {WEBHOOK_URL}")

def main() -> None:
    """Start the bot."""
    asyncio.run(setup_webhook())
    # Create the Application and pass it your bot's token.

    # on different commands - answer in Telegram

    # application.add_handler(CallbackQueryHandler(button_callback))
    # application.add_handler(CommandHandler("help", help_command))
    telebot.add_handler(CommandHandler("cat", cat))
    telebot.add_handler(CommandHandler("joke", joke))
    telebot.add_handler(CallbackQueryHandler(joke_callback_handler, pattern="^joke_"))
    telebot.add_handler(CommandHandler("rps", rps_start))
    telebot.add_handler(CallbackQueryHandler(rps_play, pattern="^rps_"))

    # on non command i.e message - echo the message on Telegram
    telebot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    # telebot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
