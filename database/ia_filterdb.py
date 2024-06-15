import logging
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER, MAX_B_TN
from utils import get_settings, save_group_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Setup MongoDB client
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance(db)

# Define MongoDB Document with umongo
@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME


async def save_file(media):
    """Save file in database"""
    try:
        file_id, file_ref = unpack_new_file_id(media.file_id)
        file_name = re.sub(r"[_\-\.+]", " ", str(media.file_name))  # Replace characters with spaces
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
        await file.commit()
    except ValidationError as e:
        logger.exception('Error occurred while saving file in database: %s', str(e))
        return False, 2
    except DuplicateKeyError:
        logger.warning(f'{getattr(media, "file_name", "NO_FILE")} is already saved in database')
        return False, 0
    except Exception as e:
        logger.error('Unexpected error occurred while saving file in database: %s', str(e))
        return False, 2
    else:
        logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
        return True, 1


async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0):
    """Retrieve search results from database."""
    try:
        if chat_id is not None:
            settings = await get_settings(int(chat_id))
            max_results = 10 if settings.get('max_btn') else int(MAX_B_TN)
        query = re.escape(query.strip()) if query else '.'
        regex = re.compile(fr'(\b|\W){query}(\b|\W)', re.IGNORECASE)
        filter = {'$or': [{'file_name': regex}, {'caption': regex}]} if USE_CAPTION_FILTER else {'file_name': regex}
        if file_type:
            filter['file_type'] = file_type
        total_results = await Media.count_documents(filter)
        cursor = Media.find(filter).sort('$natural', -1).skip(offset).limit(max_results)
        files = await cursor.to_list(length=max_results)
        next_offset = offset + max_results if offset + max_results < total_results else ''
        return files, next_offset, total_results
    except Exception as e:
        logger.error('Error occurred while fetching search results: %s', str(e))
        return [], '', 0


async def get_bad_files(query, file_type=None):
    """Retrieve files matching bad query."""
    try:
        query = re.escape(query.strip()) if query else '.'
        regex = re.compile(fr'(\b|\W){query}(\b|\W)', re.IGNORECASE)
        filter = {'$or': [{'file_name': regex}, {'caption': regex}]} if USE_CAPTION_FILTER else {'file_name': regex}
        if file_type:
            filter['file_type'] = file_type
        total_results = await Media.count_documents(filter)
        cursor = Media.find(filter).sort('$natural', -1)
        files = await cursor.to_list(length=total_results)
        return files, total_results
    except Exception as e:
        logger.error('Error occurred while fetching bad files: %s', str(e))
        return [], 0


async def get_file_details(query):
    """Retrieve details of a specific file."""
    try:
        filter = {'file_id': query}
        cursor = Media.find(filter)
        filedetails = await cursor.to_list(length=1)
        return filedetails
    except Exception as e:
        logger.error('Error occurred while fetching file details: %s', str(e))
        return []


def encode_file_id(s: bytes) -> str:
    """Encode file ID."""
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    """Encode file reference."""
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Unpack new file ID."""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(pack("<iiqq", int(decoded.file_type), decoded.dc_id, decoded.media_id, decoded.access_hash))
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
