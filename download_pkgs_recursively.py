
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


PKGS_TO_DOWNLOAD = [
# Example: {"name": "abc", "version": "1.2.3"}
]


class PkgNotFoundException(Exception):
	pass


# Bad implementation, can be improved
def create_url_with_version(pkg_obj, package_name, package_version):
	pkg_name_and_version = package_name + '-' + package_version + ".pkg"
	return r'/'.join([PKG_URL_PREFIX, "All", pkg_name_and_version])


def parse_url_from_json(package_name, package_version=None):
	with open(PKGS_URLS_JSON_PATH, "r") as fp:
		fp = io.TextIOWrapper(fp.buffer, errors='replace')

		line = fp.readline()

		while line:
			pkg_objs = yaml.load_all(line, Loader=yaml.FullLoader)
			for pkg_obj in pkg_objs:
				if pkg_obj["name"] == package_name:
					pkg_url = '/'.join([PKG_URL_PREFIX, pkg_obj["path"]])

					# Implementation can be improved to check if name+version matches url in yaml
					if package_version is not None:
						return create_url_with_version(pkg_obj, package_name, package_version)
					return pkg_url

				line = fp.readline()

	if package_version is not None:
		logging.error("Package {package_name}-{package_version} not found".format(package_name=package_name, package_version=package_version))
	else:
		logging.error("Package {package_name} not found".format(package_name=package_name))


def download_single_package(package_name, package_version=None):
	url = parse_url_from_json(package_name, package_version)
	local_package_path = os.path.join(OUTPUT_DIR, url.split(r'/')[-1])

	if os.path.exists(local_package_path):
		return local_package_path

	response = requests.get(url)

	with open(local_package_path, "wb") as fp:
		fp.write(response.content)

	return local_package_path


def extract_dependencies(local_package_path):
	tar = tarfile.open(local_package_path)
	manifest = tar.extractfile(MANIFEST_FILENAME)

	manifest_obj = json.loads(manifest.read())

	if "deps" in manifest_obj:
		for dep_name, dep_obj in manifest_obj["deps"].items():
			yield {"name": dep_name, "version": dep_obj["version"]}
	else:
		return []



def download_package(pkg, recursive=True):
	print("Downloading {package_name}".format(package_name=pkg["name"]))
	local_package_path = download_single_package(pkg["name"], pkg.get("version"))

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
