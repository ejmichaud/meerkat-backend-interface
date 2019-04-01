# Installation Instructions

First, make sure to [install redis](https://redis.io/topics/quickstart). If it's installed, you should be able to start it by executing from the terminal:
```
redis-server
```
Next, download the repository like so:
```
git clone --recurse-submodules https://github.com/ejmichaud/meerkat-backend-interface
```
I'd recommend installing the module within a virtual environment. To create the Python 2 virtual environment:
```
virtualenv -p /usr/bin/python venv
```
And activate it:
```
source venv/bin/activate
```
To install, simply `cd` into the repo
```
cd meerkat-backend-interface
```
And install requirements with pip
```
pip install -r requirements.txt
```
This will install all dependencies, and you will be ready to start up the modules.