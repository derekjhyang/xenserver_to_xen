xenserver_to_xen
================
  This project is for migrating from xenserver `*.xva` image to xen `*.img` image.

### Quickstart
1. Untar your xenserver image {{image}} with the command: `tar -xvf {image}.xva`. There are Ref:XX folder and ova.xml, where Ref:XX which contains 1MB size chunks of the image disk and ova.xml represents image spec.

2. Then grab this handy utility and run it on your untared data, as an example:
>    python xenmigrate.py –-convert=Ref:XX {image}.img
