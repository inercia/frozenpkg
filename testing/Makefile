
PYTHON=python

all: build

bin/buildout:
	$(PYTHON) bootstrap.py

build: bin/buildout
	bin/buildout -v -v

distclean:
	rm -rf bin build develop-eggs eggs parts temp
	rm -rf *.tar.gz *.rpm *.egg-info

clean: distclean	
