# Speakers: CS8409 / CS42L83 on Debian

The internal speakers are silent without the out-of-tree driver
[davidjo/snd_hda_macbookpro](https://github.com/davidjo/snd_hda_macbookpro).

## The Debian trap

`install.cirrus.driver.sh` copies `sound/pci/hda` sources to build against.
On Ubuntu it uses the `linux-source-*` tarball. On Debian none of its branches match,
so it **falls back to downloading a mainline `linux-x.y` tarball from kernel.org**.

A Debian kernel such as `6.12.100+deb13` has no exact mainline tarball, so the base
`linux-6.12` is used. The module builds against the wrong sources and at runtime does
not match the running kernel's `hda_generic` → **kernel oops** during boot.

Debian's own `linux-source-6.12` package matches the running point release exactly;
the script just has to be told to use it.

## The patch

[`cs8409-dkms-debian-linux-source.patch`](cs8409-dkms-debian-linux-source.patch):

1. `dkms.conf`: `PRE_BUILD` → `install.cirrus.driver.pre617.sh` (kernels before 6.17).
2. Adds a branch that uses `/usr/src/linux-source-6.12.tar.xz` before any kernel.org fallback.
3. Two guards so a bad build **fails loudly** instead of producing an oopsing module:
   - the package name only carries `6.12`, so after a point-release upgrade the tarball
     path stays the same while its content may still be **old** (apt may run DKMS for the
     new `linux-image` before unpacking the new `linux-source`). The `dpkg-query` version is
     compared with the target kernel; mismatch → `exit 1`.
   - on Debian without a matching `linux-source`, no kernel.org fallback → `exit 1`.

   In both cases DKMS fails, nothing is installed, and the previous kernel still boots with sound.

## Install

```bash
sudo apt install build-essential dkms linux-headers-$(uname -r) linux-source-6.12
git clone https://github.com/davidjo/snd_hda_macbookpro.git
cd snd_hda_macbookpro
git apply /path/to/cs8409-dkms-debian-linux-source.patch
sudo ./install.cirrus.driver.sh --dkms
sudo apt-mark manual linux-source-6.12 linux-headers-amd64   # keep autoremove away
```

Reboot, then:

```bash
dkms status                        # snd_hda_macbookpro ... installed
aplay -l | grep -i cs8409          # CS8409/CS42L83 Analog
journalctl -k -b | grep -i oops    # must be empty
```

The ALSA mixer has only `PCM` (no `Master`/`Speaker`). That is normal for this codec.

Also recommended: stop `unattended-upgrades` from installing kernels on its own, so a
kernel change never happens unattended in the middle of the night.

```bash
echo 'Unattended-Upgrade::Package-Blacklist { "linux-"; };' | \
  sudo tee /etc/apt/apt.conf.d/52-no-kernel-autoupgrade
```

## Better sound → [`apple-dsp/`](apple-dsp/)
