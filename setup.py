from setuptools import setup, find_packages
import os

# Read the contents of your README file
# (Assuming you have a README.md, otherwise you can remove this block)
this_directory = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "High-Precision Astrometry Pipeline wrapping Astrometry.net, SExtractor, and SCAMP."

setup(
    name='hpastrometry',
    version='1.0.0',
    description='A wrapper pipeline for high-precision astrometry using Astrometry.net, SExtractor, and SCAMP.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Jiewei Zhao',  # Replace with your name
    author_email='meow.jiewei.zhao@gmail.com', # Replace with your email
    url='https://github.com/Jiewei-Zhao/hpastrometry', # Replace with your URL
    packages=find_packages(),
    
    # Critical: This ensures the 'config' folder (.cfg, .param, etc.) is included in the installation
    include_package_data=True,
    package_data={
        'hpastrometry': ['config/*'], 
    },

    # Core Python dependencies
    install_requires=[
        'numpy',
        'astropy>=4.0',
    ],

    # Optional dependencies (install via `pip install .[mpi]`)
    extras_require={
        'mpi': ['mpi4py'],
    },

    # The Command Line Interfaces
    entry_points={
        'console_scripts': [
            'hpastrometry=hpastrometry.cli:main',
            'hpastrometry-mpi=hpastrometry.mpi_cli:main',
        ],
    },

    python_requires='>=3.8',
    
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License', # Or whichever license you use
        'Operating System :: POSIX :: Linux',
    ],
)
