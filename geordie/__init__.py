import torch
import os
import re
from .ner import GeordieNER # Geo Entity Recognition
from .disambiguation import EntityLinker # Disambiguation of entities with WikiData or OpenStreetMaps
from .role_classification import RoleClassifier # Role classification of the Geo entity
from .resources.demonyms_and_adjectives import pattern, base_transformed_dict
import nltk
from nltk.tokenize import sent_tokenize
nltk.download('punkt')



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
        self.entity_linker = EntityLinker(self.device)
        self.entity_classifier = RoleClassifier(self.device)

    def normalise_geographical_entity(self, entity):
        
        # Use re.sub to replace matches with full names (exact adjectives)
        entity = re.sub(
            pattern,
            lambda match: base_transformed_dict.get(match.group(0), match.group(0)),
            entity,
            flags=re.IGNORECASE
        )

        return entity
    
    def get_context_of_the_mention(self,text, entities):
        results = []
        if len(entities) > 0:
            # Split text into sentences
            sentences = sent_tokenize(text)
            # to remove the added keywords
            # sentences = sentences[:-2]

            # Extract sentences containing entities
            for entity in entities:
                word = entity['word']
                start_pos = entity['start']

                # Find the sentence that contains the entity based on its start position
                for sentence in sentences:
                    if text.find(sentence) <= start_pos < text.find(sentence) + len(sentence):
                        if word.startswith('##') == False:
                            sentence_marked = sentence.replace(word,f'<START>{word}<END>')
                            word_normalised = self.normalise_geographical_entity(word)
                            results.append({'context':sentence_marked.strip(),'entity': word, 'entity_normalised':word_normalised})
                            break  # Stop searching after finding the first matching sentence, because in the first mention the paper should express the relation with the place
        
        return results


    def process_text(self, text):
        # Example flow: NER -> Entity Linking -> Entity Classification
        entities = self.ner.extract_entities(text)

        # Get sentences of the mentions
        entities_in_sentence = self.get_context_of_the_mention(text, entities)
        linked_entities = self.entity_linker.link_entities(entities_in_sentence)
        
        # Classify context
        classify_context = self.entity_classifier.classify_role(linked_entities)
        
        #classified_entities = self.entity_classifier.classify(linked_entities)
        return classify_context#classified_entities

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
    # Get the path of the parent directory
    parent_dir = os.path.abspath(os.path.join(base_dir, os.pardir))
    
    # Path to the examples file
    example_file_path = os.path.join(parent_dir, 'examples', 'example.txt')

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