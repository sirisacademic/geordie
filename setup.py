from setuptools import setup, find_packages

setup(
    name="geordie",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "torch==2.1.1",
        "transformers==4.41.2"
    ],
    description="A python library for extracting geographic entities and classifying their role.",
    author="SIRIS Academic",
    author_email="nicolau.duransilva@example.com",
    url="https://github.com/sirisacademic/geordie",
    python_requires='>=3.6',
)