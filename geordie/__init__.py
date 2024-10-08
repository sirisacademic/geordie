import torch
import os
from .ner import GeordieNER # Geo Entity Recognition
from .disambiguation import EntityLinker # Disambiguation of entities with WikiData or OpenStreetMaps
from .role_classification import RoleClassifier # Role classification of the Geo entity

def get_device():
    """
    Automatically detects whether CUDA is available. If not, defaults to CPU.
    """
    if torch.cuda.is_available():
        print("Using CUDA")
        return 'cuda'
    else:
        print("Using CPU")
        return 'cpu'

class Geordie:
    def __init__(self, device=None):

        """
        Initialize the Geordie pipeline.
        :param device: (Optional) Specify 'cpu' or 'cuda'. If not provided, it is auto-detected.
        """
        # If no device is passed, it will auto-detect using get_device
        self.device = device or get_device()

        # Pass the device to each of the components
        self.ner = GeordieNER(self.device)
        self.entity_linker = EntityLinker()
        self.entity_classifier = RoleClassifier(self.device)

    def process_text(self, text):
        # Example flow: NER -> Entity Linking -> Entity Classification
        entities = self.ner.extract_entities(text)
        linked_entities = self.entity_linker.link_entities(entities)
        classified_entities = self.entity_classifier.classify(linked_entities)
        return classified_entities

# Load examples for experimentation
def load_examples():
    """
    Loads examples from the file located at 'examples/example.txt'.
    Each line in the file is considered a separate example.
    
    Returns:
        List[str]: A list of examples (each line is one example).
    """
    # Get the path of the current directory where this __init__.py file resides
    base_dir = os.path.dirname(__file__)
    
    # Path to the examples file
    example_file_path = os.path.join(base_dir, 'examples', 'example.txt')

    # Ensure the file exists before trying to read it
    if not os.path.exists(example_file_path):
        raise FileNotFoundError(f"Example file not found at: {example_file_path}")

    # Read the file and return a list of lines (examples)
    with open(example_file_path, 'r') as file:
        examples = [line.strip() for line in file.readlines()]
    
    return examples

# Function to run a single example
def run_example():
    corpus = load_examples()
    example_text = corpus[0]
    geordie = Geordie()
    
    result = geordie.process_text(example_text)
    print(f"Result for example text:\n{result}")
    return result

# Function to run a corpus of texts
def run_corpus(corpus):
    corpus = load_examples()
    geordie = Geordie()
    results = []

    for text in corpus:
        result = geordie.process_text(text)
        results.append(result)
    
    print(f"Results for corpus of texts:\n{results}")
    return results