from setuptools import setup

setup(
    name = "frozenpkg_recipe",
    entry_points = {
        'zc.buildout': [
            'rpm = frozenpkg:FrozenRPM'
        ]
    },
)
