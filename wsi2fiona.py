#!/usr/bin/env python3

# Example script that reads a directory of svs or hdpi files and
# uploads them one after another to fiona's Attach page.
#    ./wsi2fiona.py --project_name PIV_WP6 --redcap_event_name 01 /tmp/bla

import pycurl, io, hashlib, datetime, os, glob, argparse, re, json
from urllib.parse import urlencode

from tqdm import tqdm
from pathlib import Path
import requests
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

def upload_file(upload_url, fields, filepath):

    path = Path(filepath)
    total_size = path.stat().st_size
    filename = path.name

    with tqdm(
        desc=filename,
        total=total_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        with open(filepath, "rb") as f:
            # fields["files"] = ("name", f)
            fields["files"] = (filepath, f)
            e = MultipartEncoder(fields=fields)

            m = MultipartEncoderMonitor(
                e, lambda monitor: bar.update(monitor.bytes_read - bar.n)
            )
            headers = {"Content-Type": m.content_type}
            requests.post(upload_url, data=m, headers=headers, verify = False)

# Extract from filename: kidney_00040_00132_001227_002215_01_01_SOH_12710003.svs
# POST to https://fiona.ihelse.net/applications/Attach/upload.php
# files[]: (binary)
# project_name: PIV_WP6
# record_id: PIV_WP6_00040
# redcap_event_name: Event 1
# patho_stain: 12710003
# patho_databaseid: 
# patho_biopsy_nr: 
# patho_biopsy_id: 00132
# patho_image_id: 002215
# patho_block_nr: 01
# patho_slide_nr: 01
# patho_slide_id: 001227
# patho_department: SOH
# patho_specimen: kidney

parser = argparse.ArgumentParser(prog='wsi2fiona', description='Import a folder of wsi files into FIONA')
parser.add_argument("--project_name", type=str, default=None, help='---')
parser.add_argument("--redcap_event_name", type=str, default=None, help='---')
# positional argument
parser.add_argument("fileOrDirname")
args = parser.parse_args()

project_name = ""
if args.project_name != None:
    project_name = args.project_name

if project_name == "":
    print("Error: project name cannot be empty")
    exit(-1)

redcap_event_name = ""
if args.redcap_event_name != None:
    redcap_event_name = args.redcap_event_name

if redcap_event_name == "":
    print("Error: event name cannot be empty")
    exit(-1)

import_this = ""
if args.fileOrDirname != None:
    import_this = args.fileOrDirname
else:
    parser.print_help()
    exit(0)

ifiles=[]
if os.path.isfile(import_this):
    ext = os.path.splitext(import_this)[-1].lower()
    if ext == ".svs" or ext == ".ndpi":
        ifiles.append(import_this)
elif os.path.isdir(import_this):
    for root, dirs, files in os.walk(import_this, topdown=False):
        for name in files:
            # check for extension
            fn = os.path.join(root, name)
            ext = os.path.splitext(fn)[-1].lower()
            if ext == ".svs" or ext == ".ndpi":
                ifiles.append(os.path.join(root, name))

if len(ifiles) == 0:
    print("No WSI files found in %s." % (import_this))
    exit(0)
    
print("Found %d WSI images in folder, start import now" % (len(ifiles)))

for f in ifiles:
    ext = os.path.splitext(f)[-1].lower()
    fn = os.path.basename(f)
    pattern = "^(?P<specimen>[^_]*)_(?P<participant>[^_]*)_(?P<biopsyid>[^_]*)_(?P<slideid>[^_]*)_(?P<imageid>[^_]*)_(?P<blocknumber>[^_]*)_(?P<slidenumber>[^_]*)_(?P<pathodepartment>[^_]*)_(?P<stain>[^.]*).(ndpi|svs)"
    match = re.search(pattern, fn)
    if match == None:
        print("Nothing for %s" % (fn))
        continue
    # now assign the group entries to the variables we need for upload to fiona
    obj = {
        'project_name': project_name.strip(),
        'record_id': "",
        'redcap_event_name': redcap_event_name.strip(),
        'patho_stain': "",
        'patho_databaseid': "", 
        'patho_biopsy_nr': "",
        'patho_biopsy_id': "",
        'patho_image_id': "",
        'patho_block_nr': "",
        'patho_slide_nr': "",
        'patho_slide_id': "",
        'patho_department': "",
        'patho_specimen': "",
        'submit': "1"
    }
    
    if match.groupdict().get("participant") != None:
        obj["record_id"] = "%s_%s" % (project_name, match.group("participant").strip())
    if match.groupdict().get("specimen") != None:
        obj["patho_specimen"] = match.group("specimen").strip()
    if match.groupdict().get("stain") != None:
        obj["patho_stain"] = match.group("stain").strip()
    if match.groupdict().get("biopsyid") != None:
        obj["patho_biopsy_id"] = match.group("biopsyid").strip()
    if match.groupdict().get("biopsynr") != None:
        obj["patho_biopsy_nr"] = match.group("biopsynr").strip()
    if match.groupdict().get("databaseid") != None:
        obj["patho_databaseid"] = match.group("databaseid").strip()
    if match.groupdict().get("slideid") != None:
        obj["patho_slide_id"] = match.group("slideid").strip()
    if match.groupdict().get("slidenumber") != None:
        obj["patho_slide_nr"] = match.group("slidenumber").strip()
    if match.groupdict().get("blocknumber") != None:
        obj["patho_block_nr"] = match.group("blocknumber").strip()
    if match.groupdict().get("pathodepartment") != None:
        obj["patho_department"] = match.group("pathodepartment").strip()
    if match.groupdict().get("imageid") != None:
        obj["patho_image_id"] = match.group("imageid").strip()
    # now validate what is good enough as a dataset (required fields)
    required_not_empty = [ "project_name", "record_id", "redcap_event_name", "patho_image_id" ]
    validObj = True
    for entry in required_not_empty:
        if not(obj[entry]) or len(obj[entry]) == 0:
            print("Error: Missing %s, cannot import" % (entry))
            validObj = False
            break
    # seems to be ok so we can import now this:
    if validObj:
        print("Import: %s" % (json.dumps(obj, sort_keys=True, indent=2)))
        # fs = { 'files[]': open(f, 'rb') }
        # values = obj
        upload_file("https://fiona.ihelse.net/applications/Attach/upload.php", obj, f)
        # print(r.text)
    else:
        print("Error: not all values %s found in %s, skip upload" % (required_not_empty.join(", "), json.dumps(obj)))
