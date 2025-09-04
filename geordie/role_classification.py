from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer

class RoleClassifier:
    def __init__(self, device):
        """
        Initialize the Role classification component using Hugging Face's transformers pipeline.
        :param device: 'cpu' or 'cuda' to specify the computation device.
        """
        # Set device number: -1 for CPU, or the CUDA device index (typically 0)
        # device_num = 0 if device == 'cuda' else -1

        # Load the model and tokenizer
        self.model = AutoModelForSequenceClassification.from_pretrained("SIRIS-Lab/geordie-role")
        self.tokenizer = AutoTokenizer.from_pretrained("SIRIS-Lab/geordie-role")
        self.tokenizer.model_max_length = 512 #the important part

        # Initialize the NER pipeline with aggregation strategy 'simple'
        self.role_pipeline = pipeline(model=self.model, 
                                     tokenizer=self.tokenizer,
                                     task="text-classification",

                                     device=device  # Set device: -1 for CPU, or 0 (or other index) for CUDA
                                     )

    def classify_role(self, entities_in_sentence):
        """
        Perform Role classification on a single text.
        :param text: The text to process.
        :return: A list of recognized entities with aggregation.
        """
        results = []
        for item in entities_in_sentence:
            text = item['context']
            role_type = self.role_pipeline(text)
            item['role'] = role_type
            results.append(item)

        return results

    def classify_role_from_corpus(self, texts):
        """
        Perform Role classification on a corpus of texts.
        :param texts: A list of texts to process.
        :return: A list of lists, where each inner list contains entities for each text.
        """
        return 