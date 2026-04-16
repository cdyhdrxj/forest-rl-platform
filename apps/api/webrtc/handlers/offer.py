class Offer:
    def __init__(self, sdp: str, datetime: int, polite: bool = False):
        self.sdp = sdp
        self.datetime = datetime
        self.polite = polite