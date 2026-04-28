"""
geordie — Geographical Entity Object Recognition, Detection, Identification and Extraction.
"""

from __future__ import annotations

import logging

__version__ = "0.2.0"
__all__ = [
    "Geordie",
    "GeordieNER",
    "NominatimLinker",
    "GeoNamesLinker",
    "BaseLinker",
    "RoleClassifier",
    "GeoRole",
    "normalise_entity",
    "load_examples",
]

logger = logging.getLogger(__name__)

from .linkers.base import BaseLinker
from .normaliser import normalise_entity


def load_examples() -> list[str]:
    """Load bundled example texts from the package resources."""
    from importlib.resources import files as pkg_files
    example_path = pkg_files("geordie.resources") / "examples" / "example.txt"
    if not example_path.is_file():
        raise FileNotFoundError(f"Bundled example file not found: {example_path}")
    content = example_path.read_text(encoding="utf-8")
    return [line.strip() for line in content.splitlines() if line.strip()]


def get_device() -> str:
    """Auto-detect the best available device."""
    import torch
    if torch.cuda.is_available():
        logger.info("Using CUDA")
        return "cuda"
    logger.info("Using CPU")
    return "cpu"


def _ensure_punkt() -> None:
    """Download NLTK punkt tokenizer if missing."""
    import nltk
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


class Geordie:
    """
    Main pipeline: NER -> Normalisation -> Entity linking -> Role classification.
    """

    def __init__(
        self,
        device: str | None = None,
        linker: BaseLinker | None = None,
        linker_backend: str = "nominatim",
        geonames_path: str | None = None,
        dump: str = "cities15000",
        cache_path: str | None = None,
        ner_model: str | None = None,
        role_model: str | None = None,
    ):
        from nltk.tokenize import sent_tokenize
        from .ner import GeordieNER
        from .role_classification import GeoRole, RoleClassifier
        from .linkers import GeoNamesLinker, NominatimLinker

        _ensure_punkt()
        self._sent_tokenize = sent_tokenize
        self.device = device or get_device()

        ner_kwargs: dict = {"device": self.device}
        if ner_model:
            ner_kwargs["model_name"] = ner_model
        self.ner = GeordieNER(**ner_kwargs)

        if linker is not None:
            self.linker = linker
        elif linker_backend == "nominatim":
            self.linker = NominatimLinker(cache_path=cache_path)
        elif linker_backend == "geonames":
            self.linker = GeoNamesLinker(
                geonames_path=geonames_path,
                dump=dump,
                cache_path=cache_path,
            )
        else:
            raise ValueError(
                f"Unknown linker_backend={linker_backend!r}. "
                "Choose 'nominatim' or 'geonames'."
            )

        role_kwargs: dict = {"device": self.device}
        if role_model:
            role_kwargs["model_name"] = role_model
        self.role_classifier = RoleClassifier(**role_kwargs)

    def _get_context_of_mentions(self, text: str, entities: list[dict]) -> list[dict]:
        if not entities:
            return []
        sentences = self._sent_tokenize(text)
        results = []
        for entity in entities:
            word = entity["word"]
            start_pos = entity["start"]
            for sentence in sentences:
                s_idx = text.find(sentence)
                if s_idx <= start_pos < s_idx + len(sentence):
                    results.append({
                        "context":           sentence.replace(word, f"[START_ENT] {word} [END_ENT]").strip(),
                        "entity":            word,
                        "entity_normalised": normalise_entity(word),
                    })
                    break
        return results

    def process_text(self, text: str) -> list[dict]:
        entities = self.ner.extract_entities(text)
        mentions = self._get_context_of_mentions(text, entities)
        linked = self.linker.link_entities(mentions)
        return self.role_classifier.classify_role(linked)

    def process_corpus(self, texts: list[str]) -> list[list[dict]]:
        return [self.process_text(t) for t in texts]