xenserver_to_xen
================
  this project is for converting xenserver image format .xva to xen.org image format .img

### usage
`tar -xvf {image}.xva`

Then grab this handy utility and run it on your untared data, as an example:

`python xenmigrate.py –convert=Ref:3 {image}.img`
