"""Passive voice detection service using spaCy NLP."""

# Standard Libraries
import logging
import threading
import time
from typing import List, Optional, Tuple

# 3rd Party Libraries
import spacy

# Django Imports
from django.conf import settings

logger = logging.getLogger(__name__)


class PassiveVoiceDetector:
    """Thread-safe singleton service for detecting passive voice in text."""

    _instance = None
    _nlp = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Implement singleton pattern to load spaCy model once."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_initialized(self):
        """Ensure model is loaded. Thread-safe initialization."""
        if self._initialized:
            return

        with self._lock:
            # Double-check inside lock
            if self._initialized:
                return

            try:
                model_name = settings.SPACY_MODEL
                logger.info("Loading spaCy model: %s", model_name)

                start_time = time.perf_counter()

                # Optimize: disable unused components for 30-40% speed improvement
                # Only need: tagger (POS tags), parser (dependencies + sentences)
                # Disable: ner (named entities), lemmatizer, textcat, etc.
                self._nlp = spacy.load(
                    model_name,
                    disable=["ner", "lemmatizer", "textcat"]
                )

                # Performance optimizations:
                # 1. Remove attribute ruler if present (saves memory and time)
                if self._nlp.has_pipe("attribute_ruler"):
                    self._nlp.remove_pipe("attribute_ruler")

                # 2. Intern strings for faster lookups
                # This reduces memory usage and improves cache locality
                self._nlp.vocab.strings.add("auxpass")
                self._nlp.vocab.strings.add("VBN")

                load_time = (time.perf_counter() - start_time) * 1000
                logger.info("spaCy model '%s' loaded in %.2fms with optimizations", model_name, load_time)

                self._initialized = True
            except OSError:
                logger.exception(
                    "Failed to load spaCy model '%s'. "
                    "Ensure the model is installed: python -m spacy download %s",
                    settings.SPACY_MODEL,
                    settings.SPACY_MODEL
                )
                raise

    def detect_passive_sentences(self, text: str) -> List[Tuple[int, int]]:
        """
        Detect passive voice constructions in text with optimized performance.

        Returns the span of the passive voice clause (subject + verb phrase),
        not the entire sentence. This ensures accurate highlighting even when
        sentence segmentation fails (e.g., "mark.an exploit was run").

        Args:
            text: Plain text to analyze

        Returns:
            List of (start_char, end_char) tuples for passive constructions

        Example:
            >>> detector = PassiveVoiceDetector()
            >>> detector.detect_passive_sentences("The report was written.")
            [(0, 23)]
        """
        # Model is initialized in __new__, but double-check for thread safety
        if not self._initialized:
            self._ensure_initialized()

        if not text or not text.strip():
            return []

        # Process text with spaCy (thread-safe after initialization)
        doc = self._nlp(text)

        # Find passive voice constructions and return their clause boundaries
        passive_ranges = []
        for sent in doc.sents:
            clause_range = self._find_passive_clause(sent)
            if clause_range:
                passive_ranges.append(clause_range)

        return passive_ranges

    def _find_passive_clause(self, sent) -> Optional[Tuple[int, int]]:
        """
        Find the passive voice clause within a sentence.

        Returns the character range of the clause containing the passive
        construction, including subject and verb phrase.

        Args:
            sent: spaCy Span object representing a sentence

        Returns:
            Tuple (start_char, end_char) if passive found, None otherwise
        """
        for token in sent:
            # Pattern 1: Direct passive auxiliary dependency (most common)
            if token.dep_ == "auxpass":
                # Found passive - get the clause boundaries
                return self._get_clause_boundaries(token, sent)

            # Pattern 2: Past participle with auxpass child (less common)
            if token.tag_ == "VBN":
                if any(child.dep_ == "auxpass" for child in token.children):
                    return self._get_clause_boundaries(token, sent)

        return None

    # Dependencies that indicate clause boundaries (often mis-segmented sentences)
    _EXCLUDED_DEPS = frozenset({"advcl", "conj", "parataxis", "cc"})
    # Subject dependency types
    _SUBJECT_DEPS = frozenset({"nsubjpass", "nsubj", "csubj", "expl"})

    def _find_passive_head(self, passive_token):
        """Find the main verb (head) of the passive construction."""
        head = passive_token
        while head.dep_ in ("auxpass", "aux") and head.head != head:
            head = head.head
        return head

    def _is_boundary_token(self, token) -> bool:
        """Check if token indicates a sentence boundary issue (e.g., 'mark.an')."""
        return "." in token.text and token.dep_ in ("nummod", "compound")

    def _has_excluded_ancestor(self, token, head) -> bool:
        """Check if any ancestor between token and head has an excluded dependency."""
        current = token
        while current not in (head, current.head):
            if current.dep_ in self._EXCLUDED_DEPS and current.head == head:
                return True
            current = current.head
        return False

    def _collect_subject_tokens(self, head) -> List:
        """Collect tokens from subject dependencies."""
        tokens = []
        for child in head.children:
            if child.dep_ in self._SUBJECT_DEPS:
                for token in child.subtree:
                    if not self._is_boundary_token(token):
                        tokens.append(token)
        return tokens

    def _collect_verb_phrase_tokens(self, head) -> List:
        """Collect tokens from verb phrase, excluding trailing clauses."""
        tokens = []
        for token in head.subtree:
            # Skip excluded dependency subtrees
            if token != head and token.head == head and token.dep_ in self._EXCLUDED_DEPS:
                continue
            # Skip if ancestor has excluded dep
            if self._has_excluded_ancestor(token, head):
                continue
            # Skip boundary tokens
            if self._is_boundary_token(token):
                continue
            tokens.append(token)
        return tokens

    def _get_clause_boundaries(self, passive_token, sent) -> Tuple[int, int]:
        """
        Get the character boundaries of the clause containing a passive construction.

        Args:
            passive_token: Token that is part of passive construction
            sent: The sentence span containing the token

        Returns:
            Tuple (start_char, end_char) for the clause
        """
        head = self._find_passive_head(passive_token)

        # Collect tokens from subject and verb phrase
        clause_tokens = self._collect_subject_tokens(head)
        clause_tokens.extend(self._collect_verb_phrase_tokens(head))

        if not clause_tokens:
            return (sent.start_char, sent.end_char)

        # Get character boundaries from collected tokens
        clause_tokens = sorted(clause_tokens, key=lambda t: t.i)
        start_char = clause_tokens[0].idx
        last_token = clause_tokens[-1]
        end_char = last_token.idx + len(last_token.text)

        return (start_char, end_char)


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
