from setuptools import setup

setup(
    name="domus_gym",
    version="0.1",
    install_requires=[
        "gym",
        "domus_mlsim",
        "scipy <= 1.5.2",
        "stable-baselines3",
    ],  # And any other dependencies domus-gym needs
)
