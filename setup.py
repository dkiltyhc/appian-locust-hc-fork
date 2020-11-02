import os
from setuptools import setup, find_packages


with open(os.path.join('appian_locust', 'VERSION')) as version_file:
    version = version_file.read().strip()
setup(
    name="appian-locust",
    version=version or "UNKNOWN",
    description='Tools and functions to make testing Appian with Locust easier',
    author='Appian Performance & Reliability Engineering Squad',
    packages=find_packages(exclude=["contrib",
                                    "docs",
                                    "tasks",
                                    "tests",
                                    "*.tests",
                                    "*.tests.*",
                                    "tests.*"]),
    package_data={
        'appian-locust': [
            'VERSION'
        ]
    },
    install_requires=[
        "locust==1.0.2"
    ]
)
