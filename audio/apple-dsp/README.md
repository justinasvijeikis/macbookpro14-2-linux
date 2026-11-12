# Apple's speaker DSP as a PipeWire filter-chain

The driver sends the same stereo signal to all four speakers (2 tweeters, 2 woofers)
with no EQ, so the laptop sounds thin compared to macOS. macOS ships the speaker tuning
inside `AppleHDA.kext`. This recreates it with PipeWire.

## Where the numbers come from

macOS Recovery `BaseSystem.dmg` (board `Mac-CAD6701F7CEA0921`, fetched with
[`macrecovery.py`](https://github.com/acidanthera/OpenCorePkg/tree/master/Utilities/macrecovery))
→ `AppleHDA.kext/Contents/Resources/layout54.xml.zlib` (raw zlib → XML plist).

Codec subsystem `0x106b3600` uses SSM3515 amplifiers, which matches layouts 51 and 54.
Only **54** has the 4-speaker crossover, so 54 is used. (The real `layout-id` lives in EFI
device properties; the `dump_apple_properties` kernel parameter would show it. Not checked.)

`DspEqualization32` filter entries: field `2` = channel, `3` = band, `5` = type,
`6`/`7`/`8` = frequency / Q / gain as float32 stored in int32.
Types (inferred): 0 low-pass, 1 high-pass, 4 peaking, 5 low shelf, 6 high shelf.
`decode.py layout54.json` prints them once you convert the plist to JSON.

Chain: HP 63/80 Hz → ~20 EQ bands → +8 dB → limiter (ours) → crossover at 2600 Hz
(tweeters FL/FR, woofers RL/RR) → per-driver EQ.
Not reproduced: Apple's compressors, Loudness, BuzzKill, thermal protection.

## Install

```bash
sudo apt install swh-plugins          # fast_lookahead_limiter
mkdir -p ~/.config/pipewire/filter-chain.conf.d
python3 gen_pw.py > ~/.config/pipewire/filter-chain.conf.d/60-macbook-speakers.conf
systemctl --user restart filter-chain
```

`60-macbook-speakers.conf` in this folder is the same output, ready to copy.

Then in Settings → Sound:
- card profile **Analog Surround 4.0 Output + Analog Stereo Input**;
- set "Built-in Audio Analog Surround 4.0" to 100 % and control volume through
  **"MacBook Speakers (Apple DSP)"**.

Notes:
- On Debian the file **must** be in `filter-chain.conf.d`, not `pipewire.conf.d`:
  filters run in the separate `filter-chain.service`, and `pipewire.conf.d` is silently ignored.
- Loudness: `EXTRA_DB` in `gen_pw.py` (default +10 dB on top of a clip-free baseline,
  peaks caught by the limiter at −1 dBFS). More than that flattens music.
- Headphones in the 4.0 profile probably get only the tweeter channels. Not tested.

Undo: delete the conf, `systemctl --user restart filter-chain`, set the profile back to
"Analog Stereo Duplex".
