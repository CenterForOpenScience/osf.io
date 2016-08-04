from setuptools import setup

setup(
    name='osf_models',
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
        'modular-odm>=0.3.0',
        'django-typed-models>=0.5.0',
        'nameparser>=0.3.3',
        'furl>=0.5.1',
        'bleach>=1.4.1',
        'pytz>=2014.9',
        'django-dirtyfields>=1.1.0.dev0',
    ],
    dependency_links=['http://github.com/CenterForOpenScience/django-dirtyfields/tarball/add_option_to_deactivate_m2m_checks#egg=django-dirtyfields-1.1.0.dev0'],
    zip_safe=False
)
