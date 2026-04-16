class Candidate:
    def __init__(self, candidate: str, sdpMLineIndex: int, sdpMid: str, datetime: int):
        self.candidate = candidate
        self.sdpMLineIndex = sdpMLineIndex
        self.sdpMid = sdpMid
        self.datetime = datetime