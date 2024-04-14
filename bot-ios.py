import logging
import os
import re
import asyncio
from telethon import events, TelegramClient

app_id = 25875948
api_hash = 'bbc8cd4753b320c932bd56254d2917a0'

session_dir = "me_session"
os.makedirs(session_dir, exist_ok=True)
session_file = os.path.join(session_dir, "session_name")

app = TelegramClient(session_file, app_id, api_hash)
app.start()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("(APP-BFF)")
logger.info("Automatic publishing is now active ✓")

excluded_chats = []
GCAST_BLACKLIST = []
super_groups = ["super", "سوبر"]

auto_publishing_enabled = False
sending_enabled = True

@app.on(events.NewMessage(outgoing=True, pattern=r"^\.publish (\d+) (@?\S+)$"))
async def publish_to_single_chat(event):
    await event.delete()
    parameters = re.split(r'\s+', event.text.strip(), maxsplit=2)

    if len(parameters) != 3:
        return await event.reply("⌔∮ Invalid syntax. Please check the command format ⚠️")

    seconds = int(parameters[1])
    chat_usernames = parameters[2].split()
    app = event.client
    global auto_publishing_enabled
    auto_publishing_enabled = True

    message = await event.get_reply_message()

    for chat_username in chat_usernames:
        try:
            chat = await app.get_entity(chat_username)
            await publish_to_chat(app, seconds, chat.id, message, seconds)
        except Exception as e:
            await event.reply(f"⌔∮ Unable to find the group or chat {chat_username}: {str(e)}")
        await asyncio.sleep(1)

@app.on(events.NewMessage(outgoing=True, pattern=r"^\.publish_groups (\d+)$"))
async def publish_to_all_groups(event):
    await event.delete()
    parameters = "".join(event.text.split(maxsplit=1)[1:]).split(" ", 2)
    message = await event.get_reply_message()

    try:
        sleep_time = int(parameters[0])
    except Exception:
        return await event.reply("⌔∮ Invalid syntax. Please check the command format ⚠️")

    app = event.client
    global auto_publishing_enabled
    auto_publishing_enabled = True

    all_chats = await app.get_dialogs()

    while auto_publishing_enabled:
        for chat in all_chats:
            if chat.is_group:
                try:
                    if message.media:
                        await app.send_file(chat.id, message.media, caption=message.text)
                    else:
                        await app.send_message(chat.id, message.text)

                    # Log detailed information about the sent message, chat, and sleep time
                    logger.info(f"Message sent to chat {chat.id} successfully: type: {'media' if message.media else 'text'}, content: {message.text}")
                    logger.info(f"Chat details - ID: {chat.id}, Title: {chat.title}")
                    logger.info(f"Sleep time: {sleep_time} seconds")

                except Exception as e:
                    # Log detailed information about the error, chat, and sleep time
                    logger.error(f"Error in sending message to chat {chat.id}: {e}, type: {'media' if message.media else 'text'}, content: {message.text}")
                    logger.error(f"Chat details - ID: {chat.id}, Title: {chat.title}")
                    logger.error(f"Sleep time: {sleep_time} seconds")

        await asyncio.sleep(sleep_time)
    
@app.on(events.NewMessage(outgoing=True, pattern=".forGroups(?: |$)(.*)"))
async def group_broadcast(event):
    app = event.client  # Rename 'my_app' to 'app'
    text_input = event.pattern_match.group(1)

    if text_input:
        message_content = text_input
    elif event.is_reply:
        message_content = await event.get_reply_message()
    else:
        await event.edit(
            "**⌔∮ You must reply to a message, provide media, or write text along with the command**"
        )
        return

    response_message = await event.edit("⌔∮ Broadcasting in progress. Please wait.")

    error_count = 0
    success_count = 0

    try:
        async for chat_dialog in app.iter_dialogs():
            if chat_dialog.is_group:
                chat_id = chat_dialog.id
                try:
                    if chat_id not in GCAST_BLACKLIST:
                        await app.send_message(chat_id, message_content)
                        success_count += 1
                except FloodWaitError as e:
                    # Handle flood wait error (like waiting for a specified time then retrying)
                    logger.warning(f"Flood wait error. Waiting for {e.seconds} seconds.")
                    await asyncio.sleep(e.seconds)
                    success_count += 1
                except BaseException:
                    logger.error(f"Error occurred while broadcasting to chat_id: {chat_id}")
                    error_count += 1
    except Exception as e:
        logger.exception("Error occurred during broadcast", exc_info=True)
        error_count = -1  

  
    logger.info("Broadcast finished - Success: %d, Failure: %d", success_count, error_count)

    await response_message.edit(
        f"**⌔∮ Broadcasting successful to ** `{success_count}` **groups, failed to send to ** `{error_count}` **groups**"
    )
@app.on(events.NewMessage(outgoing=True, pattern=".private_broadcast(?: |$)(.*)"))
async def private_chat_broadcast(event):
    message_content = event.pattern_match.group(1)
    if not message_content and event.is_reply:
        message_content = await event.get_reply_message()
    elif not message_content:
        await event.edit("**⌔∮ Reply to a message, include media, or provide text with the command**")
        return

    # Initiating the broadcast process
    result_message = await event.edit("⌔∮ Broadcasting privately, please wait.")

    # Variables to track success and errors
    error_count = 0
    success_count = 0

    # Broadcasting to user dialogs
    async for dialog in event.client.iter_dialogs():
        if dialog.is_user and not dialog.entity.bot:
            chat_id = dialog.id
            try:
                # Check if the chat is not in the excluded list
                if chat_id not in excluded_chats:
                    # Check if the user has not saved the message
                    if not await event.client.get_messages(chat_id, ids=event.message.id):
                        await event.client.send_message(chat_id, message_content)
                        success_count += 1
                        logger.info(f"Message sent successfully to user {chat_id}")
            except BaseException as e:
                error_count += 1
                logger.error(f"Error sending message to user {chat_id}: {e}")

    # Updating the result message with the broadcast summary
    await result_message.edit(
        f"**⌔∮ Successfully broadcasted to** `{success_count}` **chats, failed to send to** `{error_count}` **chats**"
    )
    
@app.on(events.NewMessage(outgoing=True, pattern=r"^\.(stop_publishing)$"))
async def stop_auto_publishing_command(event):
    await stop_auto_publishing(event)

async def stop_auto_publishing(event):
    global auto_publishing_enabled
    auto_publishing_enabled = False
    await event.edit("**᯽︙ Automatic publishing has been successfully stopped ✓** ")
    logger.info("Automatic publishing has been stopped.")

@app.on(events.NewMessage(outgoing=True, pattern=r"^\.(check|commands|help)$"))
async def display_commands(event):
    await event.delete()
    commands_message = """
**List of Commands for the Tool**

- **Publish Command:**
  - `.publish seconds group_username`
    Auto-publish messages in a group with a time interval.
    Example: `.publish 60 @MyGroup`

- **Publish Groups Command:**
  - `.publish_groups seconds`
    Auto-publish messages in all groups with a time interval.
    Example: `.publish_groups 30`

- **ForGroups Command:**
  - `.forGroups seconds`
    Auto-publish messages in all groups with a specified time interval.
    Example: `.forGroups`

- **Private Broadcast Command:**
  - `.private_broadcast`
    Broadcast a message privately to all your contacts.
    Example: `.private_broadcast Your private message`

- **Stop Publishing Command:**
  - `.stop_publishing`
    Stop all auto-publishing commands.
    Example: `.stop_publishing`

- **Check/Commands/Help Commands:**
  - `.check`, `.commands`, `.help`
    Check tool status and display available commands.
"""
    try:
        truncated_text = commands_message
        await event.respond(file="https://graph.org//file/6619a8468eb4b0cd79af9.mp4", message=truncated_text)
    except Exception as e:
        logger.error(f"Error sending messages: {e}")

print('Automatic publishing to SourceExtra has been turned on')
app.run_until_disconnected()
