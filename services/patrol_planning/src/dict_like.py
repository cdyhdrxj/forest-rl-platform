from pydantic import BaseModel

class DictLikeModel(BaseModel):
    def __getitem__(self, key):
        if isinstance(key, str) and "." in key:
            first, rest = key.split(".", 1)
            return getattr(self, first)[rest]

        value = getattr(self, key)
        return value

    def __setitem__(self, key, value):
        if isinstance(key, str) and "." in key:
            first, rest = key.split(".", 1)
            getattr(self, first)[rest] = value
            return

        setattr(self, key, value)

    def __contains__(self, key):
        return hasattr(self, key)

    def get(self, key, default=None):
        try:
            return self[key]
        except AttributeError:
            return default