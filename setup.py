"""
AGNIYA - Homomorphic Encryption Library for Python
Setup configuration for pip installation
"""

from setuptools import setup, find_packages
import os

# Read README
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()

setup(
    name="agniya",
    version="1.0.0",
    author="AGNIYA Team",
    author_email="agniya@example.com",
    description="High-performance homomorphic encryption library with RNS compression and intelligent caching",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/adityakale838/agniya",
    project_urls={
        "Bug Tracker": "https://github.com/adityakale838/agniya/issues",
        "Documentation": "https://github.com/adityakale838/agniya#readme",
        "Source Code": "https://github.com/adityakale838/agniya",
    },
    packages=find_packages(exclude=["tests", "tests.*", "scripts", "webapp", "api"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Security :: Cryptography",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "gmpy2>=2.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
        "server": [
            "flask>=2.0.0",
            "flask-cors>=3.0.0",
        ],
        "all": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "flask>=2.0.0",
            "flask-cors>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agniya-test=test_suite:main",
        ],
    },
    keywords="homomorphic encryption paillier privacy cryptography rns compression",
    license="MIT",
    include_package_data=True,
    zip_safe=False,
)