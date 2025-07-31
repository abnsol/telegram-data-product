# telegram_scraper/scraper.py

import os
import json
import asyncio
import logging
from datetime import datetime # Make sure this is imported
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from dotenv import load_dotenv

# Custom JSON Encoder to handle datetime and bytes objects
class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat() # Convert datetime objects to ISO 8601 string
        if isinstance(obj, bytes):
            # Attempt to decode bytes to UTF-8 string.
            # If decoding fails (e.g., it's actual binary data not text),
            # fall back to string representation of bytes.
            try:
                return obj.decode('utf-8')
            except UnicodeDecodeError:
                return str(obj) # Fallback to string representation of raw bytes
        return json.JSONEncoder.default(self, obj) # Let the base class handle other types

# --- Configuration and Setup ---


# Load environment variables
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_NAME = 'telegram_scraper_session' # Name for Telethon session file
DATA_LAKE_BASE_PATH = 'data/raw' # Base path for your data lake

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler()
                    ])

# --- Telegram API Credentials Validation ---
if not API_ID or not API_HASH:
    logging.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment variables.")
    raise ValueError("Missing Telegram API credentials.")

try:
    API_ID = int(API_ID)
except ValueError:
    logging.error("TELEGRAM_API_ID must be an integer.")
    raise ValueError("Invalid Telegram API ID.")

# Initialize the Telegram client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# --- Channel Definitions ---
# General channels for message scraping
CHANNELS_FOR_MESSAGES = [
    'https://t.me/lobelia4cosmetics',
    'https://t.me/tikvahpharma',
    'https://t.me/CheMed123'
]

# Channels from which to specifically collect images for object detection
# These should ideally be a subset of CHANNELS_FOR_MESSAGES if images are tied to messages.
CHANNELS_FOR_IMAGES = [
    'https://t.me/lobelia4cosmetics',
    'https://t.me/CheMed123'
]

# --- Helper Functions for Data Lake Storage ---

def get_channel_dir_name(channel_title):
    """Sanitizes channel title for use as a directory name."""
    return "".join(c for c in channel_title if c.isalnum() or c in (' ', '_', '-')).replace(' ', '_').lower()

def ensure_directory_exists(path):
    """Ensures that a directory path exists, creating it if necessary."""
    os.makedirs(path, exist_ok=True)

async def save_message_to_json(message_dict, channel_title, scrape_date):
    """
    Saves a message dictionary to a JSON file in the data lake.
    Structure: data/raw/telegram_messages/YYYY-MM-DD/channel_name.json
    """
    channel_dir_name = get_channel_dir_name(channel_title)
    date_path = scrape_date.strftime('%Y-%m-%d')
    output_dir = os.path.join(DATA_LAKE_BASE_PATH, 'telegram_messages', date_path, channel_dir_name)
    ensure_directory_exists(output_dir)

    file_path = os.path.join(output_dir, f"{message_dict['id']}.json")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(message_dict, f, ensure_ascii=False, indent=4, cls=CustomJsonEncoder)
        logging.info(f"Saved message {message_dict['id']} from {channel_title} to {file_path}")
    except Exception as e:
        logging.error(f"Error saving message {message_dict['id']} from {channel_title}: {e}")

async def download_and_save_media(client_obj, message, channel_title, scrape_date):
    """
    Downloads media (photo/document) from a message and saves it.
    Structure: data/raw/telegram_images/YYYY-MM-DD/channel_name/message_id_media_id.ext
    """
    if not message.media:
        return None

    channel_dir_name = get_channel_dir_name(channel_title)
    date_path = scrape_date.strftime('%Y-%m-%d')
    output_dir = os.path.join(DATA_LAKE_BASE_PATH, 'telegram_images', date_path, channel_dir_name)
    ensure_directory_exists(output_dir)

    try:
        media_id_for_filename = None
        ext = 'unknown' # Default extension

        if isinstance(message.media, MessageMediaPhoto):
            # For photos, the ID is on the 'photo' object within message.media
            media_id_for_filename = message.media.photo.id
            ext = 'jpg' # Common default for photos, Telethon will determine actual

        elif isinstance(message.media, MessageMediaDocument) and message.media.document.mime_type:
            mime_type = message.media.document.mime_type
            if 'image/' in mime_type:
                media_id_for_filename = message.media.document.id
                ext = mime_type.split('/')[-1]
            else:
                logging.info(f"Skipping non-image media (MIME: {mime_type}) from message {message.id} in {channel_title}")
                return None
        else:
            logging.info(f"Skipping unsupported media type from message {message.id} in {channel_title}")
            return None

        if media_id_for_filename is None:
             logging.warning(f"Could not determine media ID for filename for message {message.id} in {channel_title}. Skipping download.")
             return None

        file_name = f"{message.id}_{media_id_for_filename}.{ext}" # Construct filename using the correct ID
        file_path = os.path.join(output_dir, file_name)

        logging.info(f"Attempting to download media from message {message.id} in {channel_title} to {file_path}...")
        # client_obj.download_media usually figures out the correct extension and renames if needed
        downloaded_path = await client_obj.download_media(message, file=file_path)

        if downloaded_path:
            logging.info(f"Downloaded media: {downloaded_path}")
            return downloaded_path
        else:
            logging.warning(f"Failed to download media for message {message.id} from {channel_title}.")
            return None
    except Exception as e:
        logging.error(f"Error downloading media for message {message.id} from {channel_title}: {e}")
        return None

# --- Main Scraper Logic ---

async def scrape_channel(client_obj, channel_link, today_date):
    """Scrapes messages and images from a single channel."""
    try:
        entity = await client_obj.get_entity(channel_link)
        channel_title = entity.title
        logging.info(f"Starting scraping for channel: {channel_title} (ID: {entity.id})")

        messages_scraped = 0
        images_downloaded = 0

        # Fetch messages (can adjust limit or use offset_date for incremental scraping)
        async for message in client_obj.iter_messages(entity, limit=None): # Use limit=None to get all
            # Save message content as JSON
            message_dict = message.to_dict()
            message_dict['channel_id'] = entity.id # Add channel ID for easier linking later
            message_dict['channel_title'] = channel_title # Add channel title
            await save_message_to_json(message_dict, channel_title, today_date)
            messages_scraped += 1

            # Check for images if this channel is designated for image collection
            if channel_link in CHANNELS_FOR_IMAGES and message.media:
                download_path = await download_and_save_media(client_obj, message, channel_title, today_date)
                if download_path:
                    images_downloaded += 1

        logging.info(f"Finished scraping {messages_scraped} messages and {images_downloaded} images from {channel_title}.")

    except Exception as e:
        logging.error(f"Critical error during scraping of {channel_link}: {e}", exc_info=True)
        # Handle specific errors like FloodWaitError if necessary:
        # if isinstance(e, FloodWaitError):
        #     logging.warning(f"Hit FloodWaitError, waiting for {e.seconds} seconds...")
        #     await asyncio.sleep(e.seconds + 5) # Wait a bit longer than required

async def main():
    """
    Main function to connect to Telegram and orchestrate channel scraping.
    """
    print("Attempting to connect to Telegram...")
    try:
        await client.start()
        if not await client.is_user_authorized():
            logging.error("Client not authorized after start. Please check API ID/Hash and possibly manual authentication.")
            return

        logging.info("Successfully connected to Telegram!")

        today_date = datetime.now() # Get current date for directory partitioning

        # Iterate through all channels for message scraping
        for channel_link in CHANNELS_FOR_MESSAGES:
            await scrape_channel(client, channel_link, today_date)

    except Exception as e:
        logging.critical(f"An unhandled error occurred in main execution: {e}", exc_info=True)
    finally:
        if client.is_connected():
            logging.info("Disconnecting from Telegram...")
            await client.disconnect()

if __name__ == '__main__':
    # Ensure the base data lake directory exists
    ensure_directory_exists(os.path.join(DATA_LAKE_BASE_PATH, 'telegram_messages'))
    ensure_directory_exists(os.path.join(DATA_LAKE_BASE_PATH, 'telegram_images'))

    asyncio.run(main())