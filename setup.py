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
    version='0.2.3',
    description='Python wrapper for FatSecret REST API',
    url='github.com/walexnelson/pyfatsecret',
    license='MIT',
    author='Alex Nelson',
    author_email='w.alexnelson@gmail.com',
    install_requires=requires,
    packages=["fatsecret"],
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
