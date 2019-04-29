# Installation Instructions

There may be other ways of doing it, but this way works for me as of 2019-03-31. First, make sure to [install redis](https://redis.io/topics/quickstart). If it's installed, you should be able to start it by executing from the terminal:
```
redis-server
```
Next, download the repository like so:
```
git clone --recurse-submodules https://github.com/ejmichaud/meerkat-backend-interface
```
It's important to include the `--recurse-submodules` because certain components rely on what's in the `./reynard/` submodule that is installed with this. 

**Now, install the following Python packages in precisely the order listed**. Of course, I'd recommend installing everything in a Python 2 virtual environment (create one with `virtualenv -p <python2 binary> venv` and then activate with `. venv/bin/activate`)

First, make sure you `cd meerkat-backend-interface`, then:

1. `pip install katversion`
2. `pip install -r requirements.txt`

You should hopefully then be able to run all the modules. 