from setuptools import setup, find_packages

setup(
    name="aforit",
    version="1.0.0",
    description="Advanced Terminal AI Agent Framework",
    author="aforit",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "aforit=aforit.main:cli",
        ],
    },
    install_requires=[
        "rich>=13.0.0",
        "prompt-toolkit>=3.0.0",
        "httpx>=0.25.0",
        "openai>=1.0.0",
        "anthropic>=0.18.0",
        "tiktoken>=0.5.0",
        "pyyaml>=6.0.0",
        "jinja2>=3.1.0",
        "beautifulsoup4>=4.12.0",
        "aiohttp>=3.9.0",
        "sqlalchemy>=2.0.0",
        "cryptography>=41.0.0",
        "pydantic>=2.0.0",
        "click>=8.1.0",
        "python-dotenv>=1.0.0",
        "cachetools>=5.3.0",
        "tenacity>=8.2.0",
        "pygments>=2.17.0",
    ],
)
