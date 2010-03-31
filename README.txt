
Example:


[rpm]
recipe         = as.recipe.frozenpkg:rpm
pkg-name       = testapp
pkg-version    = 1.0
pkg-vendor     = The Vendor
pkg-packager   = My Company
pkg-url        = http://www.mycomp.com
pkg-license    = GPL
pkg-deps       = libevent

install-prefix = /opt/testapp

eggs           = ${main:eggs}

python-version = 2.6
sys-dir        = /usr/lib/python2.6
scripts        =
                 testapp

debug          = yes
