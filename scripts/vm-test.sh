#!/bin/bash
# VirtualBox test VM for the SKJ OS EZ ISO (no root needed, user must be in vboxusers).
#
#   ./scripts/vm-test.sh create [iso]   create the VM (EFI + Secure Boot, 8 GB RAM, 4 CPUs, 60 GB disk)
#   ./scripts/vm-test.sh start          boot it (GUI window)
#   ./scripts/vm-test.sh shot [name]    screenshot -> vm/shots/<name>.png
#   ./scripts/vm-test.sh iso [iso]      put a different ISO in the DVD drive
#   ./scripts/vm-test.sh eject          remove the ISO (boot from disk after install)
#   ./scripts/vm-test.sh stop           power off
#   ./scripts/vm-test.sh info           show VM state
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VM="${SKJ_VM:-skj-os-ez-test}"
SHOTS="$ROOT/vm/shots"

latest_iso() { ls -1t "$ROOT"/out/*.iso 2>/dev/null | head -1; }

cmd="${1:-info}"
case "$cmd" in
create)
	iso="${2:-$(latest_iso)}"
	[ -f "$iso" ] || { echo "no ISO found (build one first)" >&2; exit 1; }
	if VBoxManage showvminfo "$VM" >/dev/null 2>&1; then
		echo "VM $VM already exists" >&2; exit 1
	fi
	VBoxManage createvm --name "$VM" --ostype Fedora_64 --register
	cfg=$(VBoxManage showvminfo "$VM" --machinereadable | sed -n 's/^CfgFile="\(.*\)"$/\1/p')
	disk="$(dirname "$cfg")/$VM.vdi"
	VBoxManage modifyvm "$VM" --firmware efi --memory 8192 --cpus 4 \
		--graphicscontroller vmsvga --vram 128 --accelerate-3d off \
		--nic1 nat --audio-driver default --audio-out on --usb-ohci on --mouse usbtablet \
		--boot1 dvd --boot2 disk --boot3 none --boot4 none --rtc-use-utc on
	VBoxManage createmedium disk --filename "$disk" --size 61440 --format VDI
	VBoxManage storagectl "$VM" --name SATA --add sata --controller IntelAhci --portcount 2
	VBoxManage storageattach "$VM" --storagectl SATA --port 0 --device 0 --type hdd --medium "$disk"
	VBoxManage storageattach "$VM" --storagectl SATA --port 1 --device 0 --type dvddrive --medium "$iso"
	# Secure Boot with Microsoft keys, like a normal PC
	VBoxManage modifynvram "$VM" inituefivarstore
	VBoxManage modifynvram "$VM" enrollmssignatures
	VBoxManage modifynvram "$VM" enrollorclpk
	VBoxManage modifynvram "$VM" secureboot --enable
	echo "created $VM with $iso"
	;;
start)
	VBoxManage startvm "$VM" --type gui
	;;
shot)
	mkdir -p "$SHOTS"
	name="${2:-$(date +%H%M%S)}"
	VBoxManage controlvm "$VM" screenshotpng "$SHOTS/$name.png"
	echo "$SHOTS/$name.png"
	;;
iso)
	iso="${2:-$(latest_iso)}"
	VBoxManage storageattach "$VM" --storagectl SATA --port 1 --device 0 --type dvddrive --medium "$iso"
	;;
eject)
	VBoxManage storageattach "$VM" --storagectl SATA --port 1 --device 0 --type dvddrive --medium emptydrive --forceunmount
	;;
stop)
	VBoxManage controlvm "$VM" poweroff
	;;
info)
	VBoxManage showvminfo "$VM" --machinereadable | grep -E '^(name|VMState|firmware|memory|cpus|SATA-1-0)=' || true
	;;
*)
	sed -n '2,12p' "$0"; exit 1
	;;
esac
