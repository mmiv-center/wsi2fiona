# WSI2FIONA

Import whole-slide-images into research PACS by submitting to FIONA.


### Usage

Assuming you have a folder with wsi files (.svs/.ndpi) in /tmp/bla/ you can import with

```bash
./wsi2fiona.py --project_name PIV_WP6 --redcap_event_name 01 /tmp/bla
```
