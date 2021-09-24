try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

requires = [
    'requests',
    'rauth'
]

setup(
    name='fatsecret',
    packages=['fatsecret'],
    version='0.3.0',
    description='Python wrapper for FatSecret REST API',
    author='Alex Nelson',
    author_email='w.alexnelson@gmail.com',
    url='https://github.com/walexnelson/pyfatsecret',
    license='MIT',
    install_requires=requires,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3'
    ]
)
