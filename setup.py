from setuptools import setup, find_packages

setup(
    name="schemasniff",
    version="1.0.0",
    author="baba01hacker",
    description="GraphQL schema reconstructor from introspection-disabled endpoints via field bruteforce",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Baba01hacker666/schemasniff",
    packages=find_packages(),
    package_data={"schemasniff": ["wordlist.txt"]},
    install_requires=[
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "schemasniff=schemasniff.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
