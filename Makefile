
PYTHON=python

all: build

build:
	$(PYTHON) ./setup.py bdist_egg sdist

upload-register:
	@echo 'Registering at Pypi... (settings from ~/.pydistutils.cfg)'
	$(PYTHON) ./setup.py register
	
upload: build
	@echo 'Uploading file... (settings from ~/.pydistutils.cfg)'
	$(PYTHON) ./setup.py bdist_egg sdist upload

publish: upload

clean:
	rm -rf dist build *.egg-info
	
distclean: clean
	rm -rf bin develop-eggs eggs parts temp
	rm -f `find . -name '*.pyc'`
	make -C testing distclean

