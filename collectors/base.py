"""
Base collector class for content collection
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ContentItem:
    """Represents a single piece of collected content"""
    title: str
    url: str
    source: str
    description: str = ""
    summary: str = ""  # AI-generated summary
    published_date: Optional[datetime] = None
    category: str = ""
    score: float = 0.0  # AI relevance score

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "description": self.description,
            "summary": self.summary,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "category": self.category,
            "score": self.score
        }


class BaseCollector:
    """Base class for all content collectors"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"collector.{name}")
    
    def collect(self, keywords: List[str]) -> List[ContentItem]:
        """Collect content based on keywords. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement collect()")
    
    def _clean_text(self, text: str) -> str:
        """Clean HTML tags and extra whitespace from text"""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        clean = ' '.join(clean.split())
        return clean.strip()
