from setuptools import setup

setup(name='osf_models',
      version='0.1',
      description='Django models for the OSF',
      url='http://github.com/CenterForOpenScience/osf_models',
      author='Chris Wisecarver',
      author_email='cwisecarver@cos.io',
      license='MIT',
      packages=['osf_models'],
      install_requires=[
        'django>=1.9',
        'psycopg2',
        'django-extensions==1.6.1'
      ],
      zip_safe=False)
