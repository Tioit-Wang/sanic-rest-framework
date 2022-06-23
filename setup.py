from setuptools import find_packages, setup

setup(
    name='sanic-rest-framework',
    version='1.2.3',
    packages=find_packages(),
    description="DOC...",
    author="Tioit-Wang",
    author_email='me@tioit.cc', 
    url="https://github.com/Tioit-Wang/sanic-rest-framework",
    download_url='https://codeload.github.com/Tioit-Wang/sanic-rest-framework/zip/refs/heads/main', # 下载地址
    install_requires=['sanic', 'tortoise-orm', 'ujson','PyJWT']
)