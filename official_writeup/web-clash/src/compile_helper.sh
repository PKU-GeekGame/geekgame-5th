#!/bin/bash
set -e

echo === GET CORE CHECKSUM
curl -O https://github.com/chen08209/FlClash/releases/download/v0.8.90/FlClash-0.8.90-linux-amd64.deb
dpkg --fsys-tarfile FlClash-0.8.90-linux-amd64.deb | tar -xO ./usr/share/FlClash/FlClashCore > FlClashCore
sha256=$(sha256sum FlClashCore | awk '{print $1}')

echo === CLONE PROJECT
git clone https://github.com/chen08209/FlClash
pushd FlClash/services/helper
git checkout v0.8.90

echo === COMPILE FLAG1 BINARY
TOKEN="$sha256" cargo build --release --features windows-service
cp target/release/helper ../../../helper

echo === COMPILE FLAG2 BINARY
git apply ../../../fix.patch
TOKEN="$sha256" cargo build --release --features windows-service
cp target/release/helper ../../../helper_fixed

popd