from setuptools import setup, find_packages

setup(
    name='pymcms',
    version='v0.1',
    url='https://github.com/znamlab/pymcms',
    license='MIT',
    author='Antonin Blot',
    author_email='antonin.blot@crick.ac.uk',
    description='Python wrapper for MCMS API',
    packages=find_packages(),
    install_requires=[
          'requests',
      ],
)
