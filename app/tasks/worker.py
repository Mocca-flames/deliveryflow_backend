from taskiq_redis import RedisBroker

from app.config import get_settings

settings = get_settings()

broker = RedisBroker(url=settings.REDIS_URL)
