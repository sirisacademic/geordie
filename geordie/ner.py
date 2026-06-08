"""Named Entity Recognition for geographic entities."""

from __future__ import annotations

import logging

from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "SIRIS-Lab/geordie-ner"


class GeordieNER:
    """
    NER component using a fine-tuned DistilBERT model for geographic entity recognition.

    Parameters
    ----------
    model_name : str
        HuggingFace model identifier or local path.
    device : str
        Computation device (``"cpu"``, ``"cuda"``, ``"cuda:0"``, etc.).
    max_length : int
        Maximum token length for the tokenizer.
    """

    def __init__(
        self,
        device: str = "cpu",
        model_name: str = DEFAULT_MODEL,
        max_length: int = 512,
    ):
        logger.info("Loading NER model: %s on %s", model_name, device)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tokenizer.model_max_length = max_length

        self.pipeline = pipeline(
            task="ner",
            model=self.model,
            tokenizer=self.tokenizer,
            aggregation_strategy="simple",
            device=device,
        )

    def extract_entities(self, text: str) -> list[dict]:
        """Extract geographic entities from a single text."""
        return self.pipeline(text)

    def extract_entities_batch(self, texts: list[str]) -> list[list[dict]]:
        """Extract geographic entities from a batch of texts."""
        return self.pipeline(texts)
