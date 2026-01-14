"""Passive voice detection service using spaCy NLP."""

# Standard Libraries
import logging
from typing import List, Tuple

# 3rd Party Libraries
import spacy

# Django Imports
from django.conf import settings

logger = logging.getLogger(__name__)


class PassiveVoiceDetector:
    """Singleton service for detecting passive voice in text."""

    _instance = None
    _nlp = None

    def __new__(cls):
        """Implement singleton pattern to load spaCy model once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_model()
        return cls._instance

    def _initialize_model(self):
        """Load spaCy model once at initialization using Django settings."""
        try:
            model_name = settings.SPACY_MODEL
            logger.info("Loading spaCy model from settings: %s", model_name)
            # Disable unused pipeline components for performance
            # Only need tagger (POS) and parser (dependencies + sentence segmentation)
            self._nlp = spacy.load(model_name, disable=["ner", "lemmatizer"])
            logger.info("spaCy model loaded successfully")
        except OSError as e:
            logger.exception("Failed to load spaCy model '%s': %s", settings.SPACY_MODEL, e)
            raise

    def detect_passive_sentences(self, text: str) -> List[Tuple[int, int]]:
        """
        Detect passive voice sentences in text.

        Args:
            text: Plain text to analyze

        Returns:
            List of (start_char, end_char) tuples for passive sentences

        Example:
            >>> detector = PassiveVoiceDetector()
            >>> detector.detect_passive_sentences("The report was written.")
            [(0, 23)]
        """
        if not text or not text.strip():
            return []

        doc = self._nlp(text)
        passive_ranges = []

        for sent in doc.sents:
            if self._is_passive_voice(sent):
                passive_ranges.append((sent.start_char, sent.end_char))

        return passive_ranges

    def _is_passive_voice(self, sent) -> bool:
        """
        Check if sentence contains passive voice construction.

        Looks for auxiliary verb (auxpass) + past participle (VBN).
        This pattern identifies constructions like:
        - "was written" (auxpass: was, VBN: written)
        - "were exploited" (auxpass: were, VBN: exploited)
        - "has been analyzed" (auxpass: been, VBN: analyzed)

        Args:
            sent: spaCy Span object representing a sentence

        Returns:
            True if sentence contains passive voice, False otherwise
        """
        for token in sent:
            # Direct passive auxiliary dependency
            if token.dep_ == "auxpass":
                return True

            # Past participle with auxiliary verb child
            # This catches cases where the auxpass relation is reversed
            if token.tag_ == "VBN":
                for child in token.children:
                    if child.dep_ == "auxpass":
                        return True

        return False


def get_detector() -> PassiveVoiceDetector:
    """
    Get the singleton detector instance.

    The PassiveVoiceDetector class implements singleton pattern via __new__,
    so calling this function always returns the same instance.

    Returns:
        PassiveVoiceDetector: The singleton detector instance

    Example:
        >>> from ghostwriter.modules.passive_voice.detector import get_detector
        >>> detector = get_detector()
        >>> detector.detect_passive_sentences("The bug was fixed.")
        [(0, 18)]
    """
    return PassiveVoiceDetector()
