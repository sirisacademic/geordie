import os
import re
import torch
import nltk
from nltk.tokenize import sent_tokenize

from importlib.resources import files, as_file

from .ner import GeordieNER  # Geo Entity Recognition
from .disambiguation import EntityLinker  # Disambiguation of entities with WikiData or OpenStreetMaps
from .role_classification import RoleClassifier  # Role classification of the Geo entity
from .resources.demonyms_and_adjectives import pattern, base_transformed_dict


# --- NLTK: only download if missing (avoid doing work on import) ---
def _ensure_punkt():
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)


def get_device():
    """
    Automatically detects whether CUDA is available. If not, defaults to CPU.
    """
    if torch.cuda.is_available():
        print("Using CUDA")
        return "cuda"
    else:
        print("Using CPU")
        return "cpu"


class Geordie:
    def __init__(self, device=None, entity_linker: EntityLinker | None = None):
        """
        Initialize the Geordie pipeline.
        :param device: (Optional) Specify 'cpu' or 'cuda'. If not provided, it is auto-detected.
        :param entity_linker: (Optional) Inject a pre-configured EntityLinker (e.g., with cache settings).
        """
        _ensure_punkt()

        # If no device is passed, it will auto-detect using get_device
        self.device = device or get_device()

        # Pass the device to each of the components
        self.ner = GeordieNER(self.device)
        self.entity_linker = entity_linker or EntityLinker(self.device)
        self.entity_classifier = RoleClassifier(self.device)

    def normalise_geographical_entity(self, entity: str) -> str:
        # Use re.sub to replace matches with full names (exact adjectives)
        entity = re.sub(
            pattern,
            lambda match: base_transformed_dict.get(match.group(0), match.group(0)),
            entity,
            flags=re.IGNORECASE,
        )
        return entity

    def get_context_of_the_mention(self, text: str, entities):
        results = []
        if len(entities) > 0:
            # Split text into sentences
            sentences = sent_tokenize(text)

            # Extract sentences containing entities
            for entity in entities:
                word = entity["word"]
                start_pos = entity["start"]

                # Find the sentence that contains the entity based on its start position
                for sentence in sentences:
                    s_idx = text.find(sentence)
                    if s_idx <= start_pos < s_idx + len(sentence):
                        if not word.startswith("##"):
                            sentence_marked = sentence.replace(word, f"[START_ENT] {word} [END_ENT]")
                            word_normalised = self.normalise_geographical_entity(word)
                            results.append(
                                {
                                    "context": sentence_marked.strip(),
                                    "entity": word,
                                    "entity_normalised": word_normalised,
                                }
                            )
                            # Stop after first matching sentence; usually first mention carries the relation
                            break
        return results

    def process_text(self, text: str):
        # Example flow: NER -> Entity Linking -> Entity Classification
        entities = self.ner.extract_entities(text)

        # Get sentences of the mentions
        entities_in_sentence = self.get_context_of_the_mention(text, entities)
        linked_entities = self.entity_linker.link_entities(entities_in_sentence)

        # Classify context
        classify_context = self.entity_classifier.classify_role(linked_entities)
        return classify_context


# ----------------------
# Resource-aware helpers
# ----------------------

def _read_examples_from_package() -> list[str]:
    """
    Reads examples from geordie/resources/examples/example.txt using importlib.resources.
    Returns a list of lines (examples). Raises FileNotFoundError if packaged resource is missing.
    """
    # Expected packaged path: geordie/resources/examples/example.txt
    examples_dir = files("geordie.resources") / "examples"
    example_path = examples_dir / "example.txt"

    # When a library insists on a real filesystem path, wrap with as_file(...).
    # Here we just read text directly:
    if not example_path.is_file():
        # Allow callers to detect missing packaged data
        raise FileNotFoundError(f"Packaged example file not found at: {example_path}")

    # Read text content (utf-8) and return lines
    content = example_path.read_text(encoding="utf-8")
    return [line.strip() for line in content.splitlines() if line.strip()]


def _read_examples_from_legacy_path() -> list[str]:
    """
    Backward-compatible fallback to old on-disk path: <repo-root>/examples/example.txt
    """
    base_dir = os.path.dirname(__file__)           # .../geordie
    parent_dir = os.path.abspath(os.path.join(base_dir, os.pardir))  # .../<repo-root>
    example_file_path = os.path.join(parent_dir, "examples", "example.txt")
    if not os.path.exists(example_file_path):
        raise FileNotFoundError(f"Example file not found at: {example_file_path}")
    with open(example_file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


# Public API

def load_examples() -> list[str]:
    """
    Loads examples, preferring the packaged resource at geordie/resources/examples/example.txt.
    Falls back to the old on-disk location if the packaged resource is missing.
    """
    return _read_examples_from_package()


def run_example():
    corpus = load_examples()
    example_text = corpus[0]
    geordie = Geordie()

    result = geordie.process_text(example_text)
    print(f"Result for example text:\n{result}")
    return result


def run_corpus(corpus=None):
    corpus = corpus or load_examples()
    geordie = Geordie()
    results = []

    for text in corpus:
        results.append(geordie.process_text(text))

    print(f"Results for corpus of texts:\n{results}")
    return results
