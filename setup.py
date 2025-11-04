"""
MERL-T Setup Script

Install with: pip install -e .
"""

from setuptools import setup, find_packages

setup(
    name='merl-t',
    version='0.1.0',
    description='Multi-Expert Legal Retrieval Transformer - RLCF Framework',
    author='ALIS (Artificial Legal Intelligence Society)',
    author_email='info@alis.org',
    packages=find_packages(),
    install_requires=[
        'fastapi>=0.104.0',
        'uvicorn[standard]>=0.24.0',
        'sqlalchemy>=2.0.0',
        'aiosqlite>=0.19.0',
        'greenlet>=3.0.0',
        'pydantic>=2.5.0',
        'pydantic-settings>=2.1.0',
        'pyyaml>=6.0.1',
        'numpy>=1.26.0',
        'scipy>=1.11.0',
        'gradio>=4.0.0',
        'requests>=2.31.0',
        'aiohttp>=3.9.0',
        'typing_extensions>=4.8.0',
        'asteval>=0.9.31',
        'pandas>=2.1.0',
        'click>=8.1.0',
    ],
    entry_points={
        'console_scripts': [
            'rlcf-cli=backend.rlcf_framework.cli.commands:cli',
            'rlcf-admin=backend.rlcf_framework.cli.commands:admin',
        ],
    },
    python_requires='>=3.11',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Legal Industry',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Legal',
    ],
)
