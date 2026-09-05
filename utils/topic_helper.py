import re
import random
import logging
from pyrogram.raw.functions.channels import CreateForumTopic, GetForumTopics

logger = logging.getLogger(__name__)

TOPIC_CACHE = {}

def parse_link_with_topic(link: str):
    if not link:
        return None, None, None, None
        
    link = link.strip()
    
    # 1. Private link with topic: https://t.me/c/1234567890/45/789
    m_priv_topic = re.match(r'https?://(?:t\.me|telegram\.me)/c/(\d+)/(\d+)/(\d+)', link)
    if m_priv_topic:
        return f"-100{m_priv_topic.group(1)}", int(m_priv_topic.group(3)), 'private', int(m_priv_topic.group(2))
        
    # 2. Private standard link: https://t.me/c/1234567890/789
    m_priv = re.match(r'https?://(?:t\.me|telegram\.me)/c/(\d+)/(\d+)', link)
    if m_priv:
        return f"-100{m_priv.group(1)}", int(m_priv.group(2)), 'private', None
        
    # 3. Public link with topic: https://t.me/username/45/789
    m_pub_topic = re.match(r'https?://(?:t\.me|telegram\.me)/([^/]+)/(\d+)/(\d+)', link)
    if m_pub_topic and m_pub_topic.group(1) != 'c':
        return m_pub_topic.group(1), int(m_pub_topic.group(3)), 'public', int(m_pub_topic.group(2))
        
    # 4. Public standard link: https://t.me/username/789
    m_pub = re.match(r'https?://(?:t\.me|telegram\.me)/([^/]+)/(\d+)', link)
    if m_pub and m_pub.group(1) != 'c':
        return m_pub.group(1), int(m_pub.group(2)), 'public', None
        
    return None, None, None, None

async def get_source_topic_title(client, source_chat_id, topic_id: int) -> str:
    if not topic_id or topic_id <= 1:
        return "General"
        
    cache_key = f"src_{source_chat_id}_{topic_id}"
    if cache_key in TOPIC_CACHE:
        return TOPIC_CACHE[cache_key]
        
    try:
        msg = await client.get_messages(source_chat_id, topic_id)
        if msg:
            if hasattr(msg, "forum_topic_created") and msg.forum_topic_created and hasattr(msg.forum_topic_created, "name"):
                title = msg.forum_topic_created.name
                TOPIC_CACHE[cache_key] = title
                return title
            if hasattr(msg, "action") and msg.action and hasattr(msg.action, "title"):
                title = msg.action.title
                TOPIC_CACHE[cache_key] = title
                return title
    except Exception as e:
        logger.debug(f"Could not fetch topic title via message: {e}")
        
    try:
        peer = await client.resolve_peer(source_chat_id)
        res = await client.invoke(GetForumTopics(
            channel=peer,
            offset_date=0,
            offset_id=0,
            offset_topic=0,
            limit=100
        ))
        if hasattr(res, "topics"):
            for t in res.topics:
                if getattr(t, "id", None) == topic_id and hasattr(t, "title"):
                    TOPIC_CACHE[cache_key] = t.title
                    return t.title
    except Exception as e:
        logger.debug(f"GetForumTopics on source notice: {e}")
        
    fallback = f"Topic {topic_id}"
    TOPIC_CACHE[cache_key] = fallback
    return fallback

async def get_or_create_destination_topic(client, dest_chat_id: int, topic_title: str) -> int | None:
    if not topic_title:
        return None
        
    dest_chat_id = int(dest_chat_id)
    title_clean = topic_title.strip().lower()
    cache_key = f"dest_{dest_chat_id}_{title_clean}"
    if cache_key in TOPIC_CACHE:
        return TOPIC_CACHE[cache_key]
        
    try:
        chat = await client.get_chat(dest_chat_id)
        if not getattr(chat, "is_forum", False):
            return None
            
        peer = await client.resolve_peer(dest_chat_id)
        
        try:
            res = await client.invoke(GetForumTopics(
                channel=peer,
                offset_date=0,
                offset_id=0,
                offset_topic=0,
                limit=100
            ))
            if hasattr(res, "topics"):
                for t in res.topics:
                    if hasattr(t, "title") and t.title.strip().lower() == title_clean:
                        t_id = int(t.id)
                        TOPIC_CACHE[cache_key] = t_id
                        return t_id
        except Exception as ge:
            logger.debug(f"Error checking existing topics in dest: {ge}")
            
        try:
            random_id = random.randint(1, 2**63 - 1)
            created_res = await client.invoke(CreateForumTopic(
                channel=peer,
                title=topic_title[:128],
                random_id=random_id
            ))
            
            created_topic_id = None
            if hasattr(created_res, "updates"):
                for upd in created_res.updates:
                    if hasattr(upd, "message") and hasattr(upd.message, "id"):
                        created_topic_id = int(upd.message.id)
                        break
                    elif hasattr(upd, "id"):
                        created_topic_id = int(upd.id)
                        break
            
            if created_topic_id:
                TOPIC_CACHE[cache_key] = created_topic_id
                logger.info(f"Auto-created destination topic '{topic_title}' with ID {created_topic_id}")
                return created_topic_id
                
        except Exception as ce:
            logger.error(f"Failed to create forum topic '{topic_title}' in {dest_chat_id}: {ce}")
            
    except Exception as e:
        logger.debug(f"get_or_create_destination_topic error: {e}")
        
    return None
