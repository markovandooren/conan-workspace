import setuptools

setuptools.setup(
    name='conan-workspace',
    version='0.1',
    entry_points = {
        'console_scripts': ['workspace=workspace.workspace:main']},
    packages=setuptools.find_packages()
)
