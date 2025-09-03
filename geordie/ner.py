from transformers import pipeline, AutoModelForTokenClassification, AutoTokenizer

class GeordieNER:
    def __init__(self, device):
        """
        Initialize the NER component using Hugging Face's transformers pipeline.
        :param device: 'cpu' or 'cuda' to specify the computation device.
        """
        # Set device number: -1 for CPU, or the CUDA device index (typically 0)
        # device_num = 0 if device == 'cuda' else -1

        # Load the model and tokenizer
        self.model = AutoModelForTokenClassification.from_pretrained("SIRIS-Lab/geordie-ner")
        self.tokenizer = AutoTokenizer.from_pretrained("SIRIS-Lab/geordie-ner")

        # Initialize the NER pipeline with aggregation strategy 'simple'
        self.ner_pipeline = pipeline(model=self.model, 
                                     tokenizer=self.tokenizer,
                                     task="ner",
                                     truncation=True,             # <-- important
                                     max_length=512,
                                     aggregation_strategy="simple",  # Aggregates overlapping token spans into a single entity
                                     device=device  # Set device: -1 for CPU, or 0 (or other index) for CUDA
                                     )

    def extract_entities(self, text):
        """
        Perform NER on a single text.
        :param text: The text to process.
        :return: A list of recognized entities with aggregation.
        """
        return self.ner_pipeline(text)

    def extract_entities_from_corpus(self, texts):
        """
        Perform NER on a corpus of texts.
        :param texts: A list of texts to process.
        :return: A list of lists, where each inner list contains entities for each text.
        """
        return self.ner_pipeline(texts)