# options.py
from typing import Optional
from dataclasses import dataclass


@dataclass
class Options:
    port: Optional[int] = None
    secure: Optional[bool] = None
    keyfile: Optional[str] = None
    certfile: Optional[str] = None
    type: Optional[str] = None
    mode: Optional[str] = None
    logging: Optional[str] = None