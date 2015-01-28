from setuptools import setup, find_packages

from waterbutler import __version__


def parse_requirements(requirements):
    with open(requirements) as f:
        return [l.strip('\n') for l in f if l.strip('\n') and not l.startswith('#')]


requirements = parse_requirements('requirements.txt')

setup(
    name='waterbutler',
    version=__version__,
    namespace_packages=['waterbutler', 'waterbutler.providers'],
    description='WaterButler Storage Server',
    author='Center for Open Science',
    author_email='contact@cos.io',
    url='https://github.com/CenterForOpenScience/waterbutler',
    packages=find_packages(exclude=("tests*", )),
    package_dir={'waterbutler': 'waterbutler'},
    include_package_data=True,
    # install_requires=requirements,
    zip_safe=False,
    classifiers=[
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
    ],
    provides=[
        'waterbutler.providers',
    ],
    entry_points={
        'waterbutler.providers': [
            'cloudfiles = waterbutler.providers.cloudfiles:CloudFilesProvider',
            'dropbox = waterbutler.providers.dropbox:DropboxProvider',
            'figshare = waterbutler.providers.figshare:FigshareProvider',
            'github = waterbutler.providers.github:GitHubProvider',
            'osfstorage = waterbutler.providers.osfstorage:OSFStorageProvider',
            's3 = waterbutler.providers.s3:S3Provider',
        ],
        'waterbutler.providers.tasks': [
            'osfstorage_parity = waterbutler.providers.osfstorage.tasks.parity',
            'osfstorage_backup = waterbutler.providers.osfstorage.tasks.backup',
        ]
    },
)
