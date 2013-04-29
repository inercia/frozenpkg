
PYTHON=python

all: build

bin/buildout:
	$(PYTHON) bootstrap.py

build: bin/buildout
	bin/buildout -v -v


clean:
	rm -rf bin build parts temp
	rm -rf *.tar.gz *.rpm *.egg-info

distclean: clean
	rm -rf eggs develop-eggs
	
