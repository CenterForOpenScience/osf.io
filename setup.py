from setuptools import setup, find_packages
from pip.req import parse_requirements


# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements('requirements.txt')
requirements = [str(ir.req) for ir in install_reqs]

setup(
    name='waterbutler-github',
    namespace_packages=['waterbutler'],
    version='0.0.1',
    description='WaterButler Github Storage Provider',
    author='Center for Open Science',
    author_email='contact@cos.io',
    url='https://github.com/CenterForOpenScience/waterbutler-github',
    packages=find_packages(exclude=("tests*", )),
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.4',
    ],
    provides=[
        'waterbutler.providers',
    ],
    entry_points={
        'waterbutler.providers': [
            'github = waterbutler.github.provider:GithubProvider',
        ]
    },
)
