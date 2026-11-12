# MacBook Pro 13" 2017 (MacBookPro14,2, Touch Bar + T1) on Debian 13

Fixes that are **not** already covered by the usual guides
([Dunedan/mbp-2016-linux](https://github.com/Dunedan/mbp-2016-linux), t2linux, Arch wiki),
found while running Debian 13 (trixie, kernel 6.12 LTS, GNOME 48 on Wayland) on this machine.

Everything here runs on a real MacBookPro14,2. Other 2016/2017 Touch Bar models
(MacBookPro13,2 / 13,3 / 14,3) share most of the hardware but are **untested**.

| Area | What this repo adds | Where |
|---|---|---|
| Wi-Fi (BCM43602) | 5 GHz on stock firmware, no Apple `clm_blob` | separate repo: [mbp142-bcm43602-wifi](https://github.com/justinasvijeikis/mbp142-bcm43602-wifi) |
| Speakers (CS8409) | DKMS build that does not oops on Debian kernels | [`audio/`](audio/) |
| Speakers sound | Apple's own EQ + 4-way crossover from `AppleHDA` layout 54, as a PipeWire filter-chain | [`audio/apple-dsp/`](audio/apple-dsp/) |
| T1, Touch Bar, FaceTime camera | Debian 6.12 port of [t1bridge](https://github.com/standardagents/t1bridge) + macOS-style Escape, GNOME theme, Fn chords | [`touchbar/`](touchbar/) |
| "Connection failed" every 45 s | T1 private NCM link kept away from NetworkManager / ModemManager | [`network/`](network/) |

## Status on this machine

| Works | Notes |
|---|---|
| Keyboard, trackpad | in-tree `applespi` |
| Wi-Fi 2.4 + 5 GHz | needs the NVRAM file **and a reboot** |
| Speakers | DKMS driver + optional Apple DSP |
| FaceTime camera, Touch Bar | after T1 revive ([t1-revive](https://github.com/frozenSolid/t1-revive)) + t1bridge |
| Bluetooth | works, but without Apple's `BCM.hcd` patch (slow baudrate) |
| Battery, TLP | no charge limit: `applesmc` exposes no `charge_control_end_threshold` |

| Does not work / not done | |
|---|---|
| Touch ID | t1bridge supports it, not set up here |
| Microphone | very low level (upstream driver) |
| Suspend | hangs on this machine (both `deep` and `s2idle`), disabled |

## Small gotchas worth knowing

- **Screen brightness "jumps back" darker** after you change it: that is GNOME's
  *Automatic Screen Brightness* reading the ambient light sensor next to the camera
  (`iio:device0`, name `als`). Turn it off in Settings → Power, or
  `gsettings set org.gnome.settings-daemon.plugins.power ambient-enabled false`.
- **Boot takes a minute** and `NetworkManager-wait-online` fails: the T1 NCM link
  waits 45 s for DHCP that will never come. Fixed by [`network/`](network/).
- **ACPI errors at boot** (`AE_ALREADY_EXISTS`, `\_SB.OSCP`, DMAR `UA00`) come from
  Apple firmware written for macOS. Harmless; `loglevel=3` hides them from the screen.
- Backlight is `acpi_video0` (i915 skips `intel_backlight`); it works.

## Licence

Scripts and configs in this repo: MIT (see [`LICENSE`](LICENSE)).
Patches keep the licence of the project they apply to:
t1bridge — MIT, snd_hda_macbookpro — GPL-2.0.
