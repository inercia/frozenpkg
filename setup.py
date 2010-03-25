from setuptools import setup

setup(
    name = "as.recipe.frozenpkg",
    description = "ZC Buildout recipe for freezing buildouts in RPM's, tar.gz's, etc",
    version = '0.1',
    
    # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        'Framework :: Buildout',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        ],
    keywords = 'buildout recipe',
    author = 'Alvaro Saurin',
    license = 'GPL',
    zip_safe = False,
    entry_points = {
        'zc.buildout': [
            'rpm = frozenpkg:FrozenRPM'
        ]
    },
)
