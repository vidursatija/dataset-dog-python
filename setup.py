# -*- coding: utf-8 -*-

from setuptools import setup


with open("README.md") as f:
    readme = f.read()

with open("LICENSE.md") as f:
    license = f.read()

setup(
    name="dataset_dog",
    version="0.1.0",
    description="Python client for DatasetDog",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Vidur Satija",
    author_email="vidursatija@gmail.com",
    url="https://github.com/vidursatija/dataset-dog-python",
    license=license,
    packages=["dataset_dog"],
    package_dir={"": "src"},
)
