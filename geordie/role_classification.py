"""Semantic role classification for geographic entity mentions."""

from __future__ import annotations

import logging
from enum import Enum

from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "SIRIS-Lab/geordie-role"


class GeoRole(str, Enum):
    """Semantic roles for geographic entity mentions."""

    OBJECT_OF_STUDY = "Object of Study"
    LOCATION_OF_RESEARCH = "Location of Research"
    POLICY_OR_REGULATION = "Policy or Regulation Reference"
    TARGET_AUDIENCE = "Target Audience, beneficiary or impacted entity"
    CONTEXTUAL = "Contextual and other references"


# Mapping from model label ids to human-readable roles (adjust if your model uses different labels)
LABEL_TO_ROLE = {
    "LABEL_0": GeoRole.OBJECT_OF_STUDY,
    "LABEL_1": GeoRole.LOCATION_OF_RESEARCH,
    "LABEL_2": GeoRole.POLICY_OR_REGULATION,
    "LABEL_3": GeoRole.TARGET_AUDIENCE,
    "LABEL_4": GeoRole.CONTEXTUAL,
}


class RoleClassifier:
    """
    Classifier for the semantic role of geographic entity mentions.

    Uses a fine-tuned DistilBERT sequence-classification model.

    Parameters
    ----------
    model_name : str
        HuggingFace model identifier or local path.
    device : str
        Computation device.
    max_length : int
        Maximum token length for the tokenizer.
    """

    def __init__(
        self,
        device: str = "cpu",
        model_name: str = DEFAULT_MODEL,
        max_length: int = 512,
    ):
        logger.info("Loading role classifier: %s on %s", model_name, device)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tokenizer.model_max_length = max_length

        self.pipeline = pipeline(
            task="text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            device=device,
        )

    def classify_role(self, entities_in_sentence: list[dict]) -> list[dict]:
        """
        Classify the semantic role of each entity mention.

        Adds a 'role' key (list of dicts with 'label' and 'score') to each item.
        Also adds a 'role_label' key with the human-readable role name.
        """
        results = []
        for item in entities_in_sentence:
            text = item["context"]
            role_output = self.pipeline(text)
            item["role"] = role_output

            # Map model label to human-readable role
            if role_output:
                raw_label = role_output[0].get("label", "")
                item["role_label"] = LABEL_TO_ROLE.get(raw_label, raw_label)
            else:
                item["role_label"] = None

            results.append(item)
        return results

    def classify_role_batch(self, texts: list[str]) -> list[list[dict]]:
        """Classify roles for a batch of context strings."""
        return self.pipeline(texts)
