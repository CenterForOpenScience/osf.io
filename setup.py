from setuptools import setup

setup(name='osf_models',
      version='0.0.2.dev0',
      description='Django models for the OSF',
      url='https://github.com/CenterForOpenScience/osf-models',
      author='Center for Open Science',
      author_email='pypipackages@cos.io',
      license='MIT',
      packages=['osf_models'],
      package_dir={'osf_models':'osf_models'},
      include_package_data=True,
      install_requires=[
        'django>=1.9',
        'psycopg2',
        'django-extensions==1.6.1',
        'pymongo==2.5.1',
        'git+https://github.com/CenterForOpenScience/modular-odm.git@master'
      ],
      zip_safe=False)
