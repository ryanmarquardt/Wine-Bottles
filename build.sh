#!/bin/sh

VERSION=$(head -n 1 debian/changelog | cut -d\( -f2 | cut -d\) -f1 )

verbose () { echo BUILD.SH "$@" >&2 ; "$@" ; }
indir () { ( cd "$1" ; shift ; "$@" ) ; }

pack () {
	verbose tar -cf wine-bottles.tar.bz2 --transform 's|^|dist/|' COPYING README bottle debian
}

unpack () {
	pack
	verbose tar -xf wine-bottles.tar.bz2
}

debsource () {
	indir dist verbose debuild -S -sa
}

debsourcediff () {
	indir dist verbose debuild -S -sd
}

debbinary () {
	indir dist verbose debuild
}

ppa () {
	debsourcediff
	verbose dput ppa:ryan-marquardt/ppa winebottles_${VERSION}_source.changes
}

versionbump () {
	NEWVERSION="$1"
	mv bottle bottle.orig
	sed "s/VERSION=$VERSION/VERSION=$NEWVERSION/" bottle.orig | tee bottle
	dch -v $NEWVERSION
}

"$1"
