# geordie 📌
A python library for extracting geographic entities and classifying their role.

## Features

- Named Entity Recognition (NER) to identify geographic entities (category: `GEO`).
- Integration with the OpenStreetMaps to retrieve information about recognized entities.
- Fine-tuned DistilBERT-based classification model to predict the type of mention for the entity.

## Installation

```bash
git clone https://github.com/sirisacademic/geordie.git
cd geordie
pip install -r requirements.txt
```

## Usage

```python
import geordie

# Example texts
texts = [
    "I visited Paris last summer.",
    "Mount Everest is the tallest mountain in the world."
]

# Process the texts
results = geordie.process_texts(texts)

for text_result in results:
    for entity_info in text_result:
        print(f"Entity: {entity_info['entity']}")
        print(f"Wikidata Info: {entity_info['wikidata_info']}")
        print(f"Classification: {entity_info['classification']}")
        print(f"Sentence: {entity_info['sentence']}\n")
```

## Requirements
- `transformers`
- `torch`
- `requests`


