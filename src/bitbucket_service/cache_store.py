from cachetools import TTLCache

cache = TTLCache(maxsize=1000, ttl=86400)