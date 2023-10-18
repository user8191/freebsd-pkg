
import functools
import yaml
import io
import os
import requests
import tarfile
import json


OUTPUT_DIR = r".\pkgs"
PKG_URL_PREFIX = r"https://pkg.freebsd.org/FreeBSD:13:amd64/latest"
PKGS_URLS_JSON_PATH = r"C:\users\user\Downloads\packagesite.yaml"
MANIFEST_FILENAME = "+MANIFEST"
HTTP_SUCCESS = 200


PKGS_TO_DOWNLOAD = [
# Example: {"name": "abc", "version": "1.2.3"}
]

class PkgNotFoundException(Exception):
	pass


class BadUrlException(Exception):
	pass


def log_decorator(func):
	def wrapper(*args, **kwargs):
		print("Started running {func_name} with params {args} {kwargs}".format(func_name=func.__name__, args=args, kwargs=kwargs))
		retval = func(*args, **kwargs)
		print("Finished running {func_name}, return value: {retval}".format(func_name=func.__name__, retval=retval))
		return retval
	return wrapper


def should_attempt_download_without_yaml_parse(package_version):
	return package_version is not None


@log_decorator
def create_url_without_yaml_parse(package_name, package_version):
	pkg_name_and_version = package_name + '-' + package_version + ".pkg"
	return r'/'.join([PKG_URL_PREFIX, "All", pkg_name_and_version])


# TODO: Currently doesn't check package version, can be improved
@log_decorator
def parse_url_from_yaml(package_name):		
	with open(PKGS_URLS_JSON_PATH, "r") as fp:
		fp = io.TextIOWrapper(fp.buffer, errors='replace')

		line = fp.readline()

		while line:
			pkg_objs = yaml.load_all(line, Loader=yaml.FullLoader)
			for pkg_obj in pkg_objs:
				if pkg_obj["name"] == package_name:
					return '/'.join([PKG_URL_PREFIX, pkg_obj["path"]])

				line = fp.readline()

		logging.error("Package {package_name} not found".format(package_name=package_name))


@log_decorator
def attempt_download(url):
	local_package_path = os.path.join(OUTPUT_DIR, url.split(r'/')[-1])

	if os.path.exists(local_package_path):
		return local_package_path

	response = requests.get(url)

	if response.status_code != HTTP_SUCCESS:
		raise BadUrlException("Status not 200, bad url")

	with open(local_package_path, "wb") as fp:
		fp.write(response.content)

	return local_package_path


def download_single_package(package_name, package_version=None):
	if should_attempt_download_without_yaml_parse(package_version):
		try:
			url = create_url_without_yaml_parse(package_name, package_version)
			local_package_path = attempt_download(url)
		except:
			url = parse_url_from_yaml(package_name, package_version)
			local_package_path = attempt_download(url)
	else:
		url = parse_url_from_yaml(package_name)
		local_package_path = attempt_download(url)

	return local_package_path


def extract_dependencies(local_package_path):
	try:
		tar = tarfile.open(local_package_path)
	except Exception:
		import pdb;pdb.set_trace()
	manifest = tar.extractfile(MANIFEST_FILENAME)

	manifest_obj = json.loads(manifest.read())

	if "deps" in manifest_obj:
		for dep_name, dep_obj in manifest_obj["deps"].items():
			yield {"name": dep_name, "version": dep_obj["version"]}
	else:
		return []



def download_package(pkg, recursive=True):
	print("Started downloading {package_name}".format(package_name=pkg["name"]))
	local_package_path = download_single_package(pkg["name"], pkg.get("version"))
	print("Finished downloading {package_name}".format(package_name=pkg["name"]))

	if recursive:
		dependency_pkg_names = extract_dependencies(local_package_path)

	for dependency_pkg in dependency_pkg_names:
		download_package(dependency_pkg, recursive=True)


def main():
	if not os.path.exists(OUTPUT_DIR):
		os.mkdir(OUTPUT_DIR)

	for pkg in PKGS_TO_DOWNLOAD:
		download_package(pkg, recursive=True)


if __name__ == "__main__":
	main()
