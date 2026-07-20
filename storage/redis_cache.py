import redis
import json

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)


def cache_article(article_id, data):

    key = f"article:{article_id}"

    redis_client.set(key, json.dumps(data))


def get_article(article_id):

    key = f"article:{article_id}"

    data = redis_client.get(key)

    if data:
        return json.loads(data)

    return None
