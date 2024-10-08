# geordie 📌
_Geo or die_ / _Impiccheranno **Geordie** con una corda d'oro_.

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

# Call load_examples
examples = geordie.load_examples()

# Get first example of the list
example = examples[0]

# Create instance of Geordie
my_geordie = geordie.Geordie()

# Test with an example
results = my_geordie.process_text(example)

for result in results:
    print(f"Entity: {entity_info['entity']}")
    print(f"OSM Info: {entity_info['osm']}")
    # print(f"Classification: {entity_info['osm']}")
    print(f"Sentence: {entity_info['context']}\n")
```

## Requirements
- `transformers`
- `torch`
- `requests`


