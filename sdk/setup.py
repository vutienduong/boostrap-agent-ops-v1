from setuptools import setup, find_packages

setup(
    name="agentops",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.28.0",
        "python-ulid>=3.0.0",
    ],
    extras_require={
        "dev": ["pytest", "pytest-httpx"],
    },
    python_requires=">=3.10",
)
