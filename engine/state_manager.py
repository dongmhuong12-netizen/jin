class StateManager:

    def __init__(self):
        self.cache = {}

    def _key(self, guild_id, user_id):
        return f"{guild_id}:{user_id}"

    def get(self, guild_id, user_id):
        return self.cache.get(self._key(guild_id, user_id))

    def set(self, guild_id, user_id, data):
        self.cache[self._key(guild_id, user_id)] = data

    def update(self, guild_id, user_id, patch: dict):

        key = self._key(guild_id, user_id)

        if key not in self.cache:
            self.cache[key] = {}

        self.cache[key].update(patch)

    def clear(self):
        self.cache.clear()
