
PYTHON=python2.6

all: build

bin/buildout:
	$(PYTHON) bootstrap.py

build: bin/buildout
	bin/buildout

distclean:
	rm -rf bin develop-eggs eggs parts
	rm -rf *.tar.gz *.rpm
