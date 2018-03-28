#!/bin/bash

# You probably need to update only this link
ELECTRUM_GIT_URL=git://github.com/twistproject/electrum-twist.git
BRANCH=master
NAME_ROOT=electrum-twist


# These settings probably don't need any change
export WINEPREFIX=/opt/wine64

PYHOME=c:/python27
PYTHON="wine $PYHOME/python.exe -OO -B"


# Let's begin!
cd `dirname $0`
set -e

cd tmp

if [ -d "electrum-twist-git" ]; then
    # GIT repository found, update it
    echo "Pull"
    cd electrum-twist-git
    git checkout $BRANCH
    git pull
    cd ..
else
    # GIT repository not found, clone it
    echo "Clone"
    git clone -b $BRANCH $ELECTRUM_GIT_URL electrum-twist-git
fi

cd electrum-twist-git
VERSION=`git describe --tags`
echo "Last commit: $VERSION"

cd ..

rm -rf $WINEPREFIX/drive_c/electrum-twist
cp -r electrum-twist-git $WINEPREFIX/drive_c/electrum-twist
cp electrum-twist-git/LICENCE .

# add python packages (built with make_packages)
cp -r ../../../packages $WINEPREFIX/drive_c/electrum-twist/

# add locale dir
cp -r ../../../lib/locale $WINEPREFIX/drive_c/electrum-twist/lib/

# Build Qt resources
wine $WINEPREFIX/drive_c/Python27/Lib/site-packages/PyQt4/pyrcc4.exe C:/electrum-twist/icons.qrc -o C:/electrum-twist/lib/icons_rc.py
wine $WINEPREFIX/drive_c/Python27/Lib/site-packages/PyQt4/pyrcc4.exe C:/electrum-twist/icons.qrc -o C:/electrum-twist/gui/qt/icons_rc.py

cd ..

rm -rf dist/

# build standalone version
$PYTHON "C:/pyinstaller/pyinstaller.py" --noconfirm --ascii -w deterministic.spec

# build NSIS installer
# $VERSION could be passed to the electrum.nsi script, but this would require some rewriting in the script iself.
wine "$WINEPREFIX/drive_c/Program Files (x86)/NSIS/makensis.exe" /DPRODUCT_VERSION=$VERSION electrum.nsi

cd dist
mv electrum-twist.exe $NAME_ROOT-$VERSION.exe
mv electrum-twist-setup.exe $NAME_ROOT-$VERSION-setup.exe
mv electrum-twist $NAME_ROOT-$VERSION
zip -r $NAME_ROOT-$VERSION.zip $NAME_ROOT-$VERSION
cd ..

# build portable version
cp portable.patch $WINEPREFIX/drive_c/electrum-twist
pushd $WINEPREFIX/drive_c/electrum-twist
patch < portable.patch 
popd
$PYTHON "C:/pyinstaller/pyinstaller.py" --noconfirm --ascii -w deterministic.spec
cd dist
mv electrum-twist.exe $NAME_ROOT-$VERSION-portable.exe
cd ..

echo "Done."
