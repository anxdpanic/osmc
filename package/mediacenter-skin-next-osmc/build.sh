# (c) 2014-2015 Sam Nazarko
# email@samnazarko.co.uk

#!/bin/bash

. ../common.sh

make clean

REV_skinosmc="541794126e426f7cc65c3f3bf8f929104d0b4b3d"
REV_service="6b8a82e3ba97bbcba8c44eece0a4ca93bf4c571b"
REV_skinbackup="b9121fbedb4db29b0d4aa16a97a0fa1de5cc589b"
REV_widgets="612999dc3021e1fcd57a01ef14ce473f47bfc48f"
REV_skinshortcuts="03a8905267082466a7b4b7e66c01a28fad46c19b"

echo -e "Building package mediacenter-skin-osmc"
echo -e "Downloading skin"
pull_source "https://github.com/osmc/skin.osmc/archive/${REV_skinosmc}.tar.gz" "$(pwd)/src"
if [ $? != 0 ]; then echo -e "Error downloading" && exit 1; fi
pushd src/skin.osmc-*
install_patch "../../patches" "all"
popd
echo -e "Moving files in to place"
mkdir -p files/usr/share/kodi/addons
cp -ar src/skin.osmc-${REV_skinosmc}/ files/usr/share/kodi/addons/skin.osmc
if [ -f files/usr/share/kodi/addons/skin.osmc/media/Textures.xbt ]
then
    echo "TexturePacked file detected, deleting unneeded artefacts"
    pushd files/usr/share/kodi/addons/skin.osmc/media
    find . ! -name 'Textures.xbt' -delete
    popd
fi

pull_source "https://github.com/kodi-community-addons/script.skin.helper.service/archive/${REV_service}.tar.gz" "$(pwd)/src"
cp -ar src/script.skin.helper.service-${REV_service} files/usr/share/kodi/addons/script.skin.helper.service

pull_source "https://github.com/kodi-community-addons/script.skin.helper.skinbackup/archive/${REV_skinbackup}.tar.gz" "$(pwd)/src"
cp -ar src/script.skin.helper.skinbackup-${REV_skinbackup} files/usr/share/kodi/addons/script.skin.helper.skinbackup


#pull_source "https://github.com/kodi-community-addons/script.skin.helper.widgets/archive/${REV_widgets}.tar.gz" "$(pwd)/src"
pull_source "https://kodi.gjmccarthy.co.uk/script.skin.helper.widgets-1.0.38.zip" "$(pwd)/src"
cp -ar src/script.skin.helper.widgets files/usr/share/kodi/addons/script.skin.helper.widgets

pull_source "https://github.com/marcelveldt/script.skinshortcuts/archive/${REV_skinshortcuts}.tar.gz" "$(pwd)/src"
cp -ar src/script.skinshortcuts-${REV_skinshortcuts} files/usr/share/kodi/addons/script.skinshortcuts


dpkg_build files/ mediacenter-skin-osmc.deb
