from setuptools import setup, find_packages

setup(
    name="geordie",
    version="0.1.0",
    description="Geographical entity recognition, linking and role classification",
    long_description="",
    python_requires=">=3.9",
    packages=find_packages(include=["geordie", "geordie.*"]),  # flat layout
    include_package_data=True,  # use MANIFEST.in for non-.py files
    install_requires=[
        "nltk",
        "geopy",
    ],
)