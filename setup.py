import setuptools

setuptools.setup(
    name="meerkat-backend-interface",
    version="1.0.0",
    url="https://github.com/ejmichaud/meerkat-backend-interface",
    license='MIT',

    author="Eric Michaud",
    author_email="ericjmichaud@berkeley.edu",

    description="Breakthrough Listen's interface to MeerKAT",
    long_description=open("README.md").read(),

    py_modules=[
        'distributor',
        'katcp_start',
        'katportal_start',
        ],
    packages=setuptools.find_packages(),

    install_requires=[],

    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    entry_points={
        'console_scripts': [
            'distributor = distributor:cli',
            'katcp_start = katcp_start:cli',
            'katportal_start = katportal_start:main',
            ]
        },
    )
