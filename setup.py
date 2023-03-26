import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="mathgraph",
    version="0.0.2",
    author="Puct9",
    description="Math operation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/puct9/mathgraph",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=["pydot"],
)
