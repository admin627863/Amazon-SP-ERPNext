from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in amazon_sp_erpnext/__init__.py
from amazon_sp_erpnext import __version__ as version

setup(
	name="amazon_sp_erpnext",
	version=version,
	description="ERPNext integration with Amazon Selling Partner API",
	author="Greycube",
	author_email="info@greycube.in",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
