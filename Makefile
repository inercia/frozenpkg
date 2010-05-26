
PYTHON=python2.6

all: build

build:
	$(PYTHON) ./setup.py bdist_egg sdist

upload: build
	$(PYTHON) ./setup.py bdist_egg sdist upload

clean:
	rm -rf dist build *.egg-info
	
distclean: clean
	rm -rf bin develop-eggs eggs parts
