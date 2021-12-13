import setuptools

requires = [
    'backports-abc==0.5',
    'backports.ssl-match-hostname==3.5.0.1',
    'certifi==2018.4.16',
    'chardet==3.0.4',
    'cmd2==0.8.7',
    'contextlib2==0.5.5',
    'docker==3.4.0',
    'docker-pycreds==0.3.0',
    'docopt==0.6.2',
    'enum34==1.1.6',
    'future==0.16.0',
    'futures==3.2.0',
    'idna==2.7',
    'ipaddress==1.0.22',
    'Jinja2>=2.10.1',
    'katcp==0.6.2',
    'katpoint',
    'lxml==4.6.5',
    'MarkupSafe==1.0',
    'omnijson==0.1.2',
    'pipreqs==0.4.9',
    'ply==3.11',
    'psutil==5.4.6',
    'pyparsing==2.2.0',
    'pyperclip==1.6.2',
    'redis==2.10.6',
    'requests>=2.20.0',
    'singledispatch==3.4.0.3',
    'six==1.11.0',
    'slacker==0.9.65',
    'subprocess32==3.5.2',
    'tornado==4.5.3',
    'ujson==1.35',
    'urllib3==1.23',
    'wcwidth==0.1.7',
    'weather-api==1.0.4',
    'websocket-client==0.48.0',
    'yarg==0.1.9',
    ]

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

    install_requires=requires,

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
