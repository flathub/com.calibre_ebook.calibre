#!/usr/bin/env python3
"""A custom version of the “runtime-*” in the flatpak-manifest(5) that works for more than one exported app."""
import argparse
import configparser
import os
import pathlib
import shutil
import sys
import xml.etree.cElementTree as xml_etree


__dir__ = pathlib.Path(__file__).parent
__version__ = "1"


def rename_app_icon(prefix, from_name, to_name):
	xdg_icons_dir = prefix / "share" / "icons"
	
	kill_list = set()
	
	for xdg_icons_app_path in xdg_icons_dir.glob("*/*/apps/"):
		for icon_path in map(lambda v: xdg_icons_app_path / v.name, os.scandir(xdg_icons_app_path)):
			if icon_path.with_suffix("").name == from_name:
				shutil.copy2(icon_path, icon_path.with_name(to_name + icon_path.suffix))
				kill_list.add(icon_path)
	
	return kill_list


def rename_desktop_with_icon(prefix, from_name, to_name):
	xdg_applications_dir = prefix / "share" / "applications"
	
	kill_list = set()
	
	# Read original desktop file
	desktop_file = configparser.RawConfigParser()
	desktop_file.optionxform = lambda option: option  # Prevent lower-casing of option names
	assert desktop_file.read(xdg_applications_dir / f"{from_name}.desktop", encoding="utf-8")
	
	# Copy referenced icon to acceptable file name
	icon_name = desktop_file["Desktop Entry"].get("Icon")
	if icon_name is not None and icon_name != to_name:
		kill_list |= rename_app_icon(prefix, icon_name, to_name)
		desktop_file["Desktop Entry"]["Icon"] = icon_name = to_name
	
	# Write back new (possibly modified) .desktop file
	with open(xdg_applications_dir / f"{to_name}.desktop", "w", encoding="utf-8") as f:
		desktop_file.write(f)
	
	# Queue previous desktop file for removal
	if from_name != to_name:
		kill_list.add(xdg_applications_dir / f"{from_name}.desktop")
	
	return kill_list


def rename_appdata_with_desktop(prefix, from_name, to_name):
	xdg_metainfo_dir = prefix / "share" / "metainfo"
	
	kill_list = set()
	
	appdata = xml_etree.parse(xdg_metainfo_dir / f"{from_name}.appdata.xml")
	
	# Update desktop file location to match new appid/`to_name`
	appid_elem = appdata.find(".[@type='desktop']/id")
	if appid_elem is not None:
		appid = appid_elem.text
		if appid.endswith(".desktop"):
			appid = appid[:-len(".desktop")]
		
		kill_list |= rename_desktop_with_icon(prefix, appid, to_name)
		appid_elem.text = appid = to_name
	
	# Write back new (possibly modified) appdata XML file
	appdata.write(xdg_metainfo_dir / f"{to_name}.appdata.xml", encoding="utf-8", xml_declaration=True)
	
	# Queue previous appdata XML file for removal
	if from_name != to_name:
		kill_list.add(xdg_metainfo_dir / f"{from_name}.appdata.xml")
	
	return kill_list


def main(argv=sys.argv[1:], program=sys.argv[0]):
	parser = argparse.ArgumentParser(description=__doc__, prog=pathlib.Path(program).name)
	parser.add_argument("-V", "--version", action="version", version="%(prog)s {0}".format(__version__))
	parser.add_argument("--prefix", action="store", default=pathlib.Path(os.environ.get("FLATPAK_DEST", "/app")), type=pathlib.Path)
	parser.add_argument("--appid", action="store", default=os.environ.get("FLATPAK_ID", None))
	
	try:
		args = parser.parse_args(argv)
		
		if args.appid is None:
			parser.error("Could not auto-detect target App-ID from environment, please use --appid to set it")
	except SystemExit as exc:
		return exc.code
	
	kill_list = set()
	kill_list |= rename_appdata_with_desktop(args.prefix, "calibre-gui",          f"{args.appid}")
	kill_list |= rename_appdata_with_desktop(args.prefix, "calibre-ebook-edit",   f"{args.appid}.ebook_edit")
	kill_list |= rename_appdata_with_desktop(args.prefix, "calibre-ebook-viewer", f"{args.appid}.ebook_viewer")
	kill_list |= rename_desktop_with_icon(args.prefix, "calibre-lrfviewer", f"{args.appid}.lrfviewer")
	
	# Remove now unused files
	for path in kill_list:
		path.unlink()
	
	return 0


if __name__ == "__main__":
	sys.exit(main())
