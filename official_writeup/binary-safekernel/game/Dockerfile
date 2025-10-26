FROM ubuntu:24.04

RUN apt-get update
RUN apt-get install -y qemu-system-x86 cpio

COPY run.sh aster-nix-osdk-bin.qemu_elf ./
COPY initramfs ./initramfs

CMD ["su", "-P", "-c", "./run.sh"]
