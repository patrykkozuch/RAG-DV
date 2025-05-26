"""
This module contains the Message class for representing chat messages.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Message:
    role: str
    content: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None

    def metadata_string(self):
        metadata = []

        if self.tokens_used is not None:
            metadata.append(f"Tokens used: {self.tokens_used}")
        if self.processing_time is not None:
            metadata.append(f"Processing time: {self.processing_time}s")

        return " | ".join(metadata)