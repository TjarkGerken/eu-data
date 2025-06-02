from setuptools import setup, find_packages

setup(
    name="eu_climate",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "rasterio",
        "matplotlib",
        "scikit-learn",
    ],
) 