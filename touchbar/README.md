# T1, Touch Bar and FaceTime camera on Debian 13

Without macOS the T1 chip sits in recovery mode (`lsusb`: `05ac:1281`), so there is no
Touch Bar and no camera. Two existing projects fix that, built for Arch:

1. [frozenSolid/t1-revive](https://github.com/frozenSolid/t1-revive) gets Apple-signed
   T1 firmware and stages it on the ESP, so the T1 boots on every power-on.
2. [standardagents/t1bridge](https://github.com/standardagents/t1bridge) provides the
   kernel modules and the Touch Bar daemon.

This folder has the patches that make t1bridge build and install on **Debian 13 / kernel 6.12**,
plus some desktop niceties.

## 1. Revive the T1

```bash
sudo apt install autoconf automake libtool pkgconf libzip-dev libusb-1.0-0-dev \
    libssl-dev libcurl4-openssl-dev zlib1g-dev libreadline-dev acpi-call-dkms
git clone https://github.com/frozenSolid/t1-revive && cd t1-revive
git checkout eb70a63                       # tested version
bash build.sh
sudo bin/t1-revive preflight               # the only NO is the Arch package check; ignore it
sudo bin/t1-revive backup --to ~/t1-esp-backup
sudo bin/t1-revive --no-confirm regenerate # ~5 min, no reboots
lsusb | grep 05ac:8600                     # iBridge = T1 is up
```

The private data in `/var/lib/t1-revive/private` belongs to **this one Mac**. Do not copy
it to another machine; each Mac generates its own.

## 2. Touch Bar driver: t1bridge + these patches

```bash
sudo apt install dkms linux-headers-amd64 linux-source-6.12 rustup libsystemd-dev libudev-dev
rustup toolchain install 1.88
git clone https://github.com/standardagents/t1bridge && cd t1bridge
git checkout -b debian-6.12 v0.1.12        # 81cbdf8
git am /path/to/touchbar/patches/*.patch
cargo build --locked --release -p t1-touchbar-hw --bin t1-touchbar-hw --features service
cargo build --locked --release -p t1-touchbar --bin t1-touchbar
sudo debian/install-touchbar.sh
sudo reboot
```

| Patch | |
|---|---|
| `0001` | kernel modules ported to 6.12 |
| `0002` | 64 pt Escape like macOS, GNOME accent theme, user themes + Fn assignments in `~/.config/t1bridge/touchbar.conf`, PNG decoder, Fn chords, `debian/` install/uninstall scripts |
| `0003`, `0004` | T1 private NCM link hidden from NetworkManager and ModemManager |
| `0005` | the rule from 0003 now survives the interface rename (see [`../network/`](../network/)) |

`install-touchbar.sh` installs the DKMS modules (`t1_cfgsel` goes into the initramfs),
systemd units, the media/volume provider, and a **usbmuxd udev override**. Without that
override, Debian's stock usbmuxd rule switches the T1 into a configuration where the
camera and the Touch Bar disappear.
Undo: `sudo debian/uninstall-touchbar.sh`.

## Check after reboot

```bash
lsusb | grep 05ac:8600
cat /sys/bus/usb/devices/1-3/bConfigurationValue    # 2
ls /dev/dri/touchbar /dev/video0
systemctl status t1-touchbar-hw; systemctl --user status t1-touchbar
```

## Notes

- `keyd` grabs the Touch Bar's virtual keyboard too. That is fine; keys arrive through
  "keyd virtual keyboard".
- Suspend with the T1 is untested here, because suspend hangs on this machine anyway.
