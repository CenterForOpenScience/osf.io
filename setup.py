from setuptools import setup, find_packages
from pip.req import parse_requirements


# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements('requirements.txt')
requirements = [str(ir.req) for ir in install_reqs]


setup(
    name='waterbutler',
    description='WaterButler Storage Server',
    author='Center for Open Science',
    author_email='contact@cos.io',
    url='https://github.com/CenterForOpenScience/waterbutler',
    package_dir={'waterbutler': 'waterbutler'},
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.4',
    ],
)
