from setuptools import setup

setup(
    name='foundation-api',
    packages=['foundation_api'],
    include_package_data=True,
    install_requires=[
        'flask',
        'sqlalchemy'
    ],
)