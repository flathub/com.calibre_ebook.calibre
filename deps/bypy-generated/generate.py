#!/usr/bin/env python3
"""Do something useful."""
import argparse
import json
import os
import pathlib
import subprocess
import sys


__dir__ = pathlib.Path(__file__).parent.absolute()
__version__ = "0.1.0"


CALIBRE_BYPY_SOURCES_URL = "https://raw.githubusercontent.com/kovidgoyal/calibre/master/bypy/sources.json"

# List of packages to be reused from the KDE / FDO runtime
#
# See the files “/usr/manifest-base-1.json” and “/usr/manifest.json” inside the runtime for a complete list of
# available packages. Commented out fields represent packages verified NOT to be included in the KDE 5.15
# runtime to make it easier to track which packages need to be reinvestigated on upgrade which don't.
#
# IMPORTANT: Commented out => NOT ignored => Part of generated Flatpak manifest
CALIBRE_PKG_BLACKLIST = frozenset([
	"zlib",
	"bzip2",
	"xz",
	#"unrar",
	"expat",
	"sqlite",
	"libffi",
	"hyphen",
	"openssl",
	"ncurses",
	"readline",
	"python",
	"icu",
	"libjpeg",
	"libpng",
	"libwebp",
	#"jxrlib",
	#"iconv",
	"libxml2",
	"libxslt",
	#"chmlib",
	#"optipng",
	#"mozjpeg",
	#"libusb",
	#"libmtp",
	"openjpeg",
	#"poppler",
	#"podofo",
	"libgpg-error",
	"libgcrypt",
	"glib",
	"dbus",
	#"dbusglib",
	"hunspell",
	"qt-base",
	"qt-svg",
	"qt-declarative",
	"qt-imageformats",
	"qt-webchannel",
	"qt-location",
	"qt-x11extras",
	"qt-wayland",
	"qt-sensors",
	"qt-webengine",  # Provided by the Flatpak baseapp
	"setuptools",
	"six",
	#"unrardll",
	#"lxml",
	#"pychm",
	#"html5-parser",
	#"css-parser",
	#"dateutil",
	#"dbuspython",
	#"dnspython",
	#"mechanize",
	#"feedparser",
	"markdown",
	#"html2text",
	#"soupsieve",
	#"beautifulsoup4",
	#"regex",
	#"chardet",
	#"msgpack",
	"pygments",
	#"pycryptodome",
	#"apsw",
	#"webencodings",
	#"html5lib",
	#"pillow",
	#"netifaces",
	#"psutil",
	#"ifaddr",
	#"zeroconf",
	#"toml",
	#"pyparsing",
	#"packaging",
	#"sip",
	#"pyqt-builder",
	#"pyqt-sip",
	#"pyqt",
	#"pyqt-webengine",
])

# These should be managed by bypy but aren't
BYPY_FP_MISSING_MODULES = [
	{
		"name": "setuptools-scm",
		"buildsystem": "simple",
		"build-commands": [
			'python3 setup.py install --prefix="${FLATPAK_DEST}"'
		],
		"sources": [
			{
				"type": "archive",
				"url": "https://files.pythonhosted.org/packages/cd/66/fa77e809b7cb1c2e14b48c7fc8a8cd657a27f4f9abb848df0c967b6e4e11/setuptools_scm-4.1.2.tar.gz",
				"sha256": "a8994582e716ec690f33fec70cca0f85bd23ec974e3f783233e4879090a7faa8"
			}
		]
	}
]


def main(argv=sys.argv[1:], program=sys.argv[0]):
	parser = argparse.ArgumentParser(description=__doc__, prog=pathlib.Path(program).name)
	parser.add_argument("-V", "--version", action="version", version="%(prog)s {0}".format(__version__))
	#parser.add_argument(…)
	
	try:
		args = parser.parse_args(argv)
	except SystemExit as exc:
		return exc.code
	
	# Ensure Calibre bypy sources file is available where bypy will look for it
	bypy_sources_dir = __dir__ / "bypy-data" / "src" / "bypy"
	bypy_sources_dir.mkdir(parents=True, exist_ok=True)
	bypy_sources_path = bypy_sources_dir / "sources.json"
	
	# Update Calibre sources list
	#
	# Must be checked into GIT to ensure that it will also be available when building the actual packages.
	#
	# We could use something Python internal for this, but this way we get a nice process output.
	subprocess.run(["wget", "-O", str(bypy_sources_path), CALIBRE_BYPY_SOURCES_URL], check=True)
	
	# Tell bypy where to expect the source files
	os.environ["BYPY_ROOT"] = str(__dir__ / "bypy-data")
	
	# Load relevant bypy bits as libraries (must be done after setting the environ above!)
	sys.path.insert(0, str(__dir__ / "bypy"))
	import bypy.download_sources
	
	# Some weird code for getting the *complete* dependency information (first call), narrowed
	# down to only to the actual list of dependencies that *matter* (second call)
	deps_map = bypy.download_sources.read_deps(only_buildable=False)
	pkgs = [deps_map[d["name"]] for d in bypy.download_sources.read_deps(only_buildable=True)]
	
	# Also extract the comment field for each package
	comment_map = {}
	with open(bypy_sources_path, "rb") as f:
		for item in json.load(f):
			if "name" in item and "comment" in item:
				comment_map[item["name"]] = item["comment"]
	
	fp_modules = []
	for pkg in pkgs:
		if pkg["name"] in CALIBRE_PKG_BLACKLIST:
			print(f' • Skipping package “{pkg["name"]}” (included in platform)')
			continue
		
		print(f' • Processing package “{pkg["name"]}”')
		
		# Map build-time only dependency to manifest key
		#
		# This isn't a great way for figuring this out, but it works in practice.
		fp_cleanup = []
		if "build time dependency" in comment_map.get(pkg["name"], ""):
			fp_cleanup.append("*")
		
		# The logic for expanding URLs in `bypy.download_sources.try_once` can unfortunately
		# not be invoked without also starting the actual download, so we replicate it here
		fp_source_urls = []
		for pkg_url in pkg["urls"]:
			if pkg_url == "pypi":
				# This will actually call the PyPI API and hence is pretty slow…
				print("    - Resolving PyPI URL (online): ", end="", flush=True)
				pkg_url = bypy.download_sources.get_pypi_url(pkg)
				print(pkg_url)
			elif pkg_url.startswith("github:"):
				pkg_url = bypy.download_sources.get_pypi_url(pkg_url)
			fp_source_urls.append(pkg_url)
		
		# Also copy-paste form `bypy.download_sources.verify_hash`
		fp_hash_alg, fp_hash_val = pkg["hash"].partition(":")[::2]
		fp_hash_val = fp_hash_val.strip()
		
		fp_modules.append({
			"name": pkg["name"],
			"buildsystem": "simple",
			"build-commands": [
				f'BYPY_ROOT="${{PWD}}" bypy main --no-download "{pkg["name"]}"',
			],
			"cleanup": fp_cleanup,
			"sources": [
				{
					"type": "file",
					"url": fp_source_urls[0],
					"mirror-urls": fp_source_urls[1:],
					"dest": "sources",  # Name of target directory
					"dest-filename": pkg["filename"],
					fp_hash_alg: fp_hash_val,
				},
				
				# Provide dependency information required by bypy into every build
				{
					"type": "file",
					"dest": "src/bypy",
					"path": "bypy-data/src/bypy/sources.json"
				},
			]
		})

	with open(__dir__ / "flatpak-modules.json", "w") as f:
		json.dump({
			"name": "bypy-generated",
			"modules": BYPY_FP_MISSING_MODULES + fp_modules,
		}, f, ensure_ascii=False, indent="\t", sort_keys=True)
	
	return 0


if __name__ == "__main__":
	sys.exit(main())
