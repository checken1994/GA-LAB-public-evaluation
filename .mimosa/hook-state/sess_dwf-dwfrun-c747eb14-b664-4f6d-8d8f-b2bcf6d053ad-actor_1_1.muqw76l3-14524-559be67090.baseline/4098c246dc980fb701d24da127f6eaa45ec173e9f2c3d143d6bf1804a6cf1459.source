"""
[OPT-15] Literature — DomainExpert for literature (uses Gutenberg).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
This SLM:
  1. Checks local knowledge (classic authors, literary periods)
  2. Falls back to Gutenberg DataSource for book metadata
  3. Returns SLMResponse with answer + confidence + source
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Literature(Base):
    """Literature DomainExpert — books, authors, literary movements."""

    # Local knowledge: classic authors and their notable works
    _AUTHORS: dict[str, dict[str, Any]] = {
        "shakespeare": {
            "info": "William Shakespeare (1564-1616) was an English playwright, poet, and "
                    "actor, widely regarded as the greatest writer in the English language.",
            "works": ["Hamlet", "Romeo and Juliet", "Macbeth", "Othello", "King Lear",
                      "A Midsummer Night's Dream", "The Tempest"],
        },
        "dickens": {
            "info": "Charles Dickens (1812-1870) was an English writer and social critic. "
                    "Created some of the world's best-known fictional characters.",
            "works": ["A Tale of Two Cities", "Great Expectations", "Oliver Twist",
                      "A Christmas Carol", "David Copperfield", "Bleak House"],
        },
        "tolstoy": {
            "info": "Leo Tolstoy (1828-1910) was a Russian writer regarded as one of the "
                    "greatest authors of all time.",
            "works": ["War and Peace", "Anna Karenina", "The Death of Ivan Ilyich",
                      "Resurrection"],
        },
        "austen": {
            "info": "Jane Austen (1775-1817) was an English novelist known for her witty "
                    "social commentary and realistic portrayal of women's lives.",
            "works": ["Pride and Prejudice", "Sense and Sensibility", "Emma",
                      "Persuasion", "Northanger Abbey", "Mansfield Park"],
        },
        "hemingway": {
            "info": "Ernest Hemingway (1899-1961) was an American novelist, short-story "
                    "writer, and journalist. Known for his economical, understated style.",
            "works": ["The Old Man and the Sea", "A Farewell to Arms", "For Whom the Bell "
                      "Tolls", "The Sun Also Rises"],
        },
        "orwell": {
            "info": "George Orwell (1903-1950) was an English novelist, essayist, and "
                    "critic. Known for his social critique and opposition to totalitarianism.",
            "works": ["Nineteen Eighty-Four", "Animal Farm", "Homage to Catalonia"],
        },
        "hugo": {
            "info": "Victor Hugo (1802-1885) was a French poet, novelist, and dramatist of "
                    "the Romantic movement.",
            "works": ["Les Misérables", "The Hunchback of Notre-Dame"],
        },
        "dostoevsky": {
            "info": "Fyodor Dostoevsky (1821-1881) was a Russian novelist, philosopher, and "
                    "essayist. Known for psychological depth and exploration of human nature.",
            "works": ["Crime and Punishment", "The Brothers Karamazov", "The Idiot",
                      "Notes from Underground"],
        },
    }

    _MOVEMENTS: dict[str, str] = {
        "what is romanticism": "Romanticism was an artistic, literary, musical, and intellectual "
                                "movement (late 18th to mid-19th century) emphasizing emotion, "
                                "individualism, and nature as a source of inspiration. Key figures: "
                                "Wordsworth, Shelley, Hugo, Goethe.",
        "what is realism": "Realism was a 19th-century literary movement that sought to depict "
                            "everyday life accurately, without romantic idealization. Key figures: "
                            "Balzac, Flaubert, Tolstoy, Dickens.",
        "what is modernism": "Modernism was an early 20th-century movement characterized by a "
                              "break with traditional forms, experimentation with narrative "
                              "structure, and focus on inner consciousness. Key figures: Joyce, "
                              "Woolf, Proust, Kafka.",
        "what is gothic literature": "Gothic literature is a genre combining fiction, horror, "
                                       "death, and romance. Originated in 18th-century England "
                                       "with Horace Walpole's 'The Castle of Otranto'.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Literature", domain="literature", config=config)
        self._gutenberg = None
        try:
            from scp.data_sources.gutenberg import GutenbergDataSource
            self._gutenberg = GutenbergDataSource()
        except Exception as e:
            logger.debug(f"Literature Gutenberg init: {e}", exc_info=True)

    def predict(self, question: str) -> SLMResponse:
        start = self._start_timer()
        cached = self.get_cached(question)
        if cached:
            self._end_timer(start, True)
            return cached

        q = question.strip()
        q_lower = q.lower()
        answer = ""
        confidence = 0.0
        reasoning = ""
        evidence: dict[str, Any] = {}

        # Path 1: author lookup (local knowledge)
        for name, info in self._AUTHORS.items():
            if name in q_lower:
                answer = info["info"] + " Notable works: " + ", ".join(info["works"]) + "."
                confidence = 0.85
                reasoning = f"local_knowledge: author '{name}'"
                evidence = {"value": answer, "source": "local_knowledge",
                            "author": name, "works": info["works"]}
                break

        # Path 2: literary movement lookup
        if not answer:
            for key, val in self._MOVEMENTS.items():
                if key in q_lower:
                    answer = val
                    confidence = 0.8
                    reasoning = f"local_knowledge: movement '{key}'"
                    evidence = {"value": val, "source": "local_knowledge", "movement": key}
                    break

        # Path 3: Gutenberg fallback for specific book queries
        if not answer and self._gutenberg and self._gutenberg.enabled:
            try:
                result = self._gutenberg.query(q)
                if result and result.get("value"):
                    meta = result.get("metadata", {})
                    authors = ", ".join(meta.get("authors", []))
                    answer = (f"'{result['value']}' by {authors}. "
                              f"Downloads: {meta.get('download_count', '?')}. "
                              f"Languages: {', '.join(meta.get('languages', []))}. "
                              f"Available on Project Gutenberg (ID: {meta.get('gutenberg_id', '?')}).")
                    confidence = 0.75
                    reasoning = "GutenbergDataSource: book search"
                    evidence = result
            except Exception as e:
                logger.debug(f"Literature Gutenberg query: {e}", exc_info=True)

        if not answer:
            confidence = 0.0
            reasoning = "Literature pattern not recognized — try 'Who was Shakespeare?' or 'What is romanticism?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="literature", reasoning=reasoning,
            evidence=evidence, slm_name=self.name,
            processing_time=time.time() - start,
        )
        self.cache_response(question, resp)
        self._end_timer(start, confidence > 0.3)
        return resp

    def get_confidence(self, question: str, answer: str) -> float:
        if not answer:
            return 0.0
        return 0.75 if "Gutenberg" in answer else 0.85


# [OPT-7] Alias — "SLM" in SCP means "Specialized Logic Module" (DomainExpert).
LiteratureExpert = Literature
