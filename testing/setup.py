
from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name = 'frozen_test_app',
      version = version,
      description = "frozen test app",
      long_description = """A frozen test app""",
      classifiers = [],
      keywords = 'frozen test app',
      author = 'tester',
      author_email = 'tester@gmail.com',
      url = 'www.testing.com',
      license ='BSD',
      packages = find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data = True,
      zip_safe = False,
      install_requires = [
          # -*- Extra requirements: -*-
      ],
      entry_points = """
      # -*- Entry points: -*-
      """,
      )
