
all: build

build:
	python ./setup.py bdist_egg sdist

upload: build
	python ./setup.py bdist_egg sdist upload

clean:
	rm -rf dist build *.egg-info
	
distclean: clean
	rm -rf bin develop-eggs eggs parts
