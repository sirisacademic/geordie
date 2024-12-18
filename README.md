# geordie 📌🅾️💀
_Geo or die_ / _Impiccheranno **Geordie** con una corda d'oro_ / _**G**eographical **E**ntity **O**bject **R**ecognition, **D**etection, **I**dentification and **E**xtraction_

A python library for extracting geographic entities and classifying their role.

## Features

- Named Entity Recognition (NER) to identify geographic entities (category: `GEO`).
- Integration with the OpenStreetMaps to retrieve information about recognized entities.
    - Including demonym, country code, and adjective, normalisation into country name.
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

example = examples[0]
result = my_geordie.process_text(example)
for item in result:
    print(item['context'])
    print(f"--> Entity: {item['osm']['name']} | Type: {list(item['osm']['address'].keys())[0]} | Place: {item['osm']['address']['county']}")
    print(f"--> Type of mention to the geo entity: {item['role'][0]['label']}")
    print('\n')
```

## Module description
### Named Entity Recognition (NER) to identify geographic entities (category: `GEO`)
We train a new NER model, specifically targeting location-related entities, by fine-tuning a DistilBERT model for token classification tasks using a combination of several datasets from different languages and domains. The datasets used for fine-tuning include English, Spanish, Italian, French, German, and Catalan, each offering annotated data for specific categories of interest such as locations, buildings, and geographical entities.

- 🤗 **Model available at: https://huggingface.co/SIRIS-Lab/geordie-ner**

#### Datasets
The a sample of the following datasets were utilized for fine-tuning:

| Language       | Dataset Name                                         | Categories of Interest               | Link to Dataset        |
|----------------|------------------------------------------------------|--------------------------------------|------------------------|
| Catalan        | Catalan Entity Identification and Linking (CEIL)      | GPE, Location, Building              | [CEIL Link](#)          |
| Multilingual   | europarl-ner (en, it, es, de)                         | LOC                                  | [europarl-ner](#)       |
| English        | FewNERD                                               | Location, Building                   | [FewNERD](#)            |
| Multilingual   | MultiNERD                                              | LOC                                  | [MultiNERD](#)          |

#### Evaluation
We evaluate the fine-tuned model on test sets from each dataset.

| Metric              | Precision | Recall   | F1 Score | Number      |
|---------------------|-----------|----------|----------|-------------|
| **GEO Entity**             | 0.902467  | 0.906956 | 0.904706 | 24,526      |

### Entity normalisation with OpenStreetMaps

Demonyms, adjetives, and country codes, are transformed into the country name, to improve performance in OpenStreetMaps search.
We evaluate the search on a collection of 170 mentions identified in Catalan, and we obtain an **accuracy of 0.82**.

## Identification of the role of the geographic entity

Lorem ipsum.

## Requirements
- `transformers`
- `torch`
- `requests`


