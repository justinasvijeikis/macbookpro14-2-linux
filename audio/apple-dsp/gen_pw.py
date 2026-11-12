#!/usr/bin/env python3
"""Generate a PipeWire filter-chain from Apple AppleHDA layout54 SoftwareDSP (MacBookPro14,2, SSM3515).

Decoded Apple DspEqualization32 filter types (inferred):
  0 = lowpass, 1 = highpass, 4 = peaking, 5 = low shelf, 6 = high shelf.
Shelves use Q=0.707 (Apple's shelf Q semantics unknown; PipeWire/WebAudio shelf ~ S=1).
Dynamics (compressors, loudness, BuzzKill, thermal protection) are not reproduced.
"""
import cmath, math, sys

FS = 48000.0

# --- layout54, IntSpeaker SignalProcessing[0] -------------------------------
PRE = [  # identical for L and R
    # DspFunction0: subsonic high-pass
    ("hp", 63.0, 0.850, 0), ("hp", 80.0, 0.707, 0),
    # DspFunction3
    ("pk", 123.2, 0.500, 3.03), ("pk", 3295.5, 2.140, -6.06),
    ("hs", 11000.0, 0.707, -6.00), ("hs", 2779.9, 0.707, 3.00),
    # DspFunction5
    ("pk", 70.7, 3.182, -2.15), ("hs", 345.0, 0.707, -17.50),
    ("pk", 70.0, 3.421, -1.50), ("pk", 100.0, 2.315, -18.50),
    ("pk", 200.0, 1.905, -12.50), ("pk", 145.0, 4.366, -5.00),
    ("pk", 1250.0, 3.960, -4.00), ("pk", 1900.0, 2.315, 3.50),
    ("pk", 3550.0, 1.228, -2.00), ("pk", 7100.0, 5.307, -5.50),
    ("pk", 10600.0, 2.000, 3.00), ("pk", 13382.9, 2.200, -9.85),
    ("pk", 5510.4, 3.493, 1.52),
]
PRE_GAIN_DB = 20 * math.log10(2.5119)  # DspFunction6 DspGainStage (+8 dB)
EXTRA_DB = 10.0   # extra loudness on top of the clip-free baseline; peaks caught by the limiter
LIMIT_DB = -1.0  # limiter ceiling (dBFS)

TWEETER = [  # DspFunction8 (splitter outputs 0,1)
    ("hp", 2600.0, 0.756, 0), ("hp", 2600.0, 0.731, 0),
    ("pk", 2495.9, 1.923, -6.81), ("pk", 14214.1, 1.336, -12.54),
    ("pk", 6300.0, 4.000, -5.00), ("pk", 10018.2, 1.952, -7.20),
]
WOOFER = [  # DspFunction9 (splitter outputs 2,3)
    ("lp", 2600.0, 0.774, 0), ("lp", 2600.0, 0.762, 0),
    ("pk", 855.7, 1.182, -14.78), ("pk", 2059.2, 2.253, -3.63),
    ("pk", 5387.5, 1.325, -14.96), ("pk", 8750.9, 1.797, -4.01),
    ("pk", 315.0, 2.721, -6.41), ("pk", 328.2, 2.392, -2.15),
    ("pk", 437.0, 2.463, -8.55),
]

LABEL = {"hp": "bq_highpass", "lp": "bq_lowpass", "pk": "bq_peaking",
         "hs": "bq_highshelf", "ls": "bq_lowshelf"}


def coeffs(t, f0, q, g):
    """RBJ cookbook biquad."""
    A = 10 ** (g / 40)
    w = 2 * math.pi * f0 / FS
    c, s = math.cos(w), math.sin(w)
    al = s / (2 * q)
    if t == "lp":
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]; a = [1 + al, -2 * c, 1 - al]
    elif t == "hp":
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]; a = [1 + al, -2 * c, 1 - al]
    elif t == "pk":
        b = [1 + al * A, -2 * c, 1 - al * A]; a = [1 + al / A, -2 * c, 1 - al / A]
    elif t in ("hs", "ls"):
        sq = 2 * math.sqrt(A) * al
        if t == "hs":
            b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
            a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
        else:
            b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
            a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    return b, a


def resp(chain, f):
    z = cmath.exp(-1j * 2 * math.pi * f / FS)
    h = 1
    for t, f0, q, g in chain:
        b, a = coeffs(t, f0, q, g)
        h *= (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    return h


def freqs():
    f = 20.0
    while f < 20000:
        yield f
        f *= 2 ** (1 / 24)


def db(x):
    return 20 * math.log10(max(abs(x), 1e-12))


def analyse():
    g = 10 ** (PRE_GAIN_DB / 20)
    peak = -999
    rows = []
    for f in freqs():
        p = resp(PRE, f) * g
        tw, wo = p * resp(TWEETER, f), p * resp(WOOFER, f)
        peak = max(peak, db(tw), db(wo))
        rows.append((f, db(p), db(tw), db(wo), db(tw + wo)))
    return peak, rows


def build(out_gain_db):
    nodes, links = [], []

    def chain(prefix, ch):
        names = []
        for i, (t, f0, q, g) in enumerate(ch):
            n = f"{prefix}{i}"
            nodes.append(f'{{ type = builtin name = {n} label = {LABEL[t]} '
                         f'control = {{ "Freq" = {f0} "Q" = {q} "Gain" = {g} }} }}')
            if names:
                links.append(f'{{ output = "{names[-1]}:Out" input = "{n}:In" }}')
            names.append(n)
        return names

    ins, outs = [], []
    # stereo look-ahead limiter after the common EQ, before the crossover
    # (crossover branches never exceed 0 dB, so the outputs stay below LIMIT_DB)
    total = PRE_GAIN_DB + out_gain_db + EXTRA_DB
    lim_gain = min(total, 12.0)            # swh limiter input gain is capped at +20 dB
    pre_lin = 10 ** ((total - lim_gain) / 20)  # remainder applied by a mixer before the limiter
    nodes.append(f'{{ type = ladspa name = limiter plugin = fast_lookahead_limiter_1913 label = fastLookaheadLimiter '
                 f'control = {{ "Input gain (dB)" = {lim_gain:.2f} "Limit (dB)" = {LIMIT_DB} "Release time (s)" = 0.08 }} }}')
    for idx, side in ((1, "L"), (2, "R")):
        pre = chain(f"pre{side}_", PRE)
        tw = chain(f"tw{side}_", TWEETER)
        wo = chain(f"wo{side}_", WOOFER)
        nodes.append(f'{{ type = builtin name = pregain{side} label = mixer control = {{ "Gain 1" = {pre_lin:.6f} }} }}')
        links.append(f'{{ output = "{pre[-1]}:Out" input = "pregain{side}:In 1" }}')
        links.append(f'{{ output = "pregain{side}:Out" input = "limiter:Input {idx}" }}')
        links.append(f'{{ output = "limiter:Output {idx}" input = "{tw[0]}:In" }}')
        links.append(f'{{ output = "limiter:Output {idx}" input = "{wo[0]}:In" }}')
        ins.append(f'"{pre[0]}:In"')
        outs.append((f'"{tw[-1]}:Out"', f'"{wo[-1]}:Out"'))

    # output order: FL FR RL RR = tweeter L, tweeter R, woofer L, woofer R
    out_ports = [outs[0][0], outs[1][0], outs[0][1], outs[1][1]]
    ind = "\n                    "
    return f"""# MacBookPro14,2 speakers: Apple AppleHDA layout54 SoftwareDSP (EQ + 2600 Hz crossover)
# Generated by audio/apple-dsp/gen_pw.py - do not edit by hand.
# Source: macOS Recovery BaseSystem.dmg -> AppleHDA.kext/Contents/Resources/layout54.xml.zlib
# Apple's compressors/thermal protection are NOT reproduced. Instead: limiter input gain {PRE_GAIN_DB + out_gain_db + EXTRA_DB:+.1f} dB
# (= clip-free baseline {PRE_GAIN_DB + out_gain_db:+.1f} dB + extra {EXTRA_DB:+.1f} dB), swh fast_lookahead_limiter ceiling {LIMIT_DB} dBFS.
context.modules = [
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "MacBook Speakers (Apple DSP)"
            media.name       = "MacBook Speakers (Apple DSP)"
            filter.graph = {{
                nodes = [{ind}{ind.join(nodes)}
                ]
                links = [{ind}{ind.join(links)}
                ]
                inputs  = [ {' '.join(ins)} ]
                outputs = [ {' '.join(out_ports)} ]
            }}
            capture.props = {{
                node.name      = "effect_input.macbook_speakers"
                audio.channels = 2
                audio.position = [ FL FR ]
                media.class    = Audio/Sink
                priority.session = 2000
            }}
            playback.props = {{
                node.name      = "effect_output.macbook_speakers"
                audio.channels = 4
                audio.position = [ FL FR RL RR ]
                node.passive   = true
                target.object  = "alsa_output.pci-0000_00_1f.3.analog-surround-40"
            }}
        }}
    }}
]
"""


if __name__ == "__main__":
    peak, rows = analyse()
    out_gain = -peak - 1.0  # 1 dB headroom
    if "--table" in sys.argv:
        print(f"peak per-speaker gain (incl. +8 dB stage): {peak:+.1f} dB -> output trim {out_gain:+.1f} dB")
        print(f"{'Hz':>7} {'pre':>7} {'tweet':>7} {'woof':>7} {'sum':>7}   (after trim)")
        for i, (f, p, t, w, s) in enumerate(rows):
            if i % 4 == 0:
                print(f"{f:7.0f} {p+out_gain:7.1f} {t+out_gain:7.1f} {w+out_gain:7.1f} {s+out_gain:7.1f}")
    else:
        sys.stdout.write(build(out_gain))
