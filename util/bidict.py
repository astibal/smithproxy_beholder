class BiDict:
    def __init__(self):
        self.forward = {}
        self.inverse = {}

    def insert(self, key, value):
        if key in self.forward:
            old_val = self.forward[key]
            del self.inverse[old_val]
        if value in self.inverse:
            old_key = self.inverse[value]
            del self.forward[old_key]
        self.forward[key] = value
        self.inverse[value] = key

    def remove(self, key_or_value):
        value_from_forward = self.forward.get(key_or_value)
        if value_from_forward:
            del self.forward[key_or_value]
            del self.inverse[value_from_forward]
        else:
            key_from_inverse = self.inverse.get(key_or_value)
            if key_from_inverse:
                del self.inverse[key_or_value]
                del self.forward[key_from_inverse]

    def get_forward(self, key):
        return self.forward.get(key)

    def get_inverse(self, value):
        return self.inverse.get(value)

    def get_any(self, key_or_value):
        return self.forward.get(key_or_value) or self.inverse.get(key_or_value)
