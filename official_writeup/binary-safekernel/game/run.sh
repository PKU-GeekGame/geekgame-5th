#!/bin/bash

set -e

pushd initramfs
find . | cpio -ov --format=newc > ../initramfs.cpio
popd

QEMU_LOG=qemu.log
if [ -f anticheat.sh ]; then
	source anticheat.sh
fi

qemu-system-x86_64 \
	-kernel	aster-nix-osdk-bin.qemu_elf \
	-append 'init=/bin/busybox -- sh /init.sh' \
	-initrd initramfs.cpio \
	-cpu host -enable-kvm -machine microvm,rtc=on -m 4G -smp 2 \
	-chardev stdio,id=con,mux=on,logfile=$QEMU_LOG \
	-serial chardev:con -monitor none -nographic \
	-device virtio-serial-device -device virtconsole,chardev=con \
	-device isa-debug-exit,iobase=0xf4,iosize=4 -no-reboot
