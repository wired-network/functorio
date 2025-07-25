import logging
import os
from typing import List
from datetime import datetime, timedelta
from telegram import ForceReply, Update, Message
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import argparse
import random
import multiprocessing

from httpx import AsyncClient

client = AsyncClient()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

FLY_API_TOKEN = os.getenv("FLY_API_TOKEN")
fly_auth_header = {
    "Authorization": f"Bearer {FLY_API_TOKEN}"
}

# Global variable to store authorized chat_id
authorized_chat_id = None

async def is_authorized(update: Update) -> bool:
    """Check if the chat_id is authorized to use the bot."""
    global authorized_chat_id
    current_chat_id = update.effective_chat.id
    
    if authorized_chat_id is None:
        # First time usage, authorize this chat
        authorized_chat_id = current_chat_id
        logger.info(f"Authorized chat_id: {authorized_chat_id}")
        return True
    
    return current_chat_id == authorized_chat_id

async def get_machine_list(fly_api_token: str) -> List[dict]:
    """Fetch the list of machines from Fly.io."""
    response = await client.get("https://api.machines.dev/v1/apps/functorio/machines", headers=fly_auth_header)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to fetch machines: {response.status_code}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
        
    context.user_data['start_time'] = datetime.now()
    
    machines = await get_machine_list(FLY_API_TOKEN)
    if len(machines) != 1:
        await update.message.reply_text(
            "There should be exactly one machine running. Please check your setup."
        )
        return
    machine = machines[0]
    id = machine.get("id")
    if not id:
        await update.message.reply_text(
            "Machine ID not found. Please check your setup."
        )
        return

    response = await client.post(f"https://api.machines.dev/v1/apps/functorio/machines/{id}/start", headers=fly_auth_header)
    if response.status_code == 200:
        await update.message.reply_text("Machine started successfully. You must wait 5 minutes before using /stop.")
    else:
        await update.message.reply_text(f"Failed to start machine: {response.status_code}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
        
    # Check if start was called and if 5 minutes have passed
    start_time = context.user_data.get('start_time')
    if start_time:
        time_elapsed = datetime.now() - start_time
        if time_elapsed < timedelta(minutes=5):
            remaining_time = timedelta(minutes=5) - time_elapsed
            remaining_minutes = int(remaining_time.total_seconds() // 60)
            remaining_seconds = int(remaining_time.total_seconds() % 60)
            await update.message.reply_text(
                f"You need to wait {remaining_minutes} minutes and {remaining_seconds} seconds after /start before you can /stop."
            )
            return
    
    machines = await get_machine_list(FLY_API_TOKEN)
    if len(machines) != 1:
        await update.message.reply_text(
            "There should be exactly one machine running. Please check your setup."
        )
        return
    machine = machines[0]

    id = machine.get("id")
    if not id:
        await update.message.reply_text(
            "Machine ID not found. Please check your setup."
        )
        return

    response = await client.post(f"https://api.machines.dev/v1/apps/functorio/machines/{id}/stop", headers=fly_auth_header)
    if response.status_code == 200:
        await update.message.reply_text("Machine stopped successfully.")
        context.user_data.pop('start_time', None)
    else:
        await update.message.reply_text(f"Failed to stop machine: {response.status_code}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    if not await is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
        
    await update.message.reply_text(
        "Use /start@functoriobot to start the Functorio machine.\n"
        "Use /stop@functoriobot to stop the Functorio machine.\n"
        "Note: You must wait 5 minutes after /start before you can use /stop.\n"
        "Use /help@functoriobot to get this message."
    )




def main() -> None:
    """Start the bot."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Functorio Bot")
    parser.add_argument(
        "--token",
        type=str,
        default=os.getenv("TELEGRAM_BOT_TOKEN"),
        required=False,
        help="Telegram Bot Token",
    )
    args = parser.parse_args()

    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token(args.token)
        .build()
    )

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("nevergonnagiveyouup", lambda update, context: update.message.reply_text("https://www.youtube.com/watch?v=dQw4w9WgXcQ")))

    # on non command i.e message - echo the message on Telegram
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()