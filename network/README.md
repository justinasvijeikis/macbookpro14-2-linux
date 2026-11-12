# "Connection failed" every 45 s and a 1-minute boot

Once the T1 is running (`05ac:8600`), it exposes a USB NCM network interface
(`apple_t1_ncm`, MAC `ac:de:48:00:11:22`, named `enxacde48001122`). It is a private
link to the T1, not a network. NetworkManager treats it as a wired connection:

- it tries DHCP, times out after 45 s, and retries forever → GNOME shows
  *"Activation of network connection failed"* over and over;
- `NetworkManager-wait-online.service` waits for it → **boot stalls for ~60 s**
  (`systemd-analyze blame`).

## Why the obvious udev rule is not enough

The natural fix is a udev rule that sets `NM_UNMANAGED=1` on `ACTION=="add"`.
It does not work: right after `add`, the interface is **renamed** (`usb0` →
`enxacde48001122`). The rename creates a `move` event, which runs the rules again,
and the properties set only on `add` are lost. Check it with:

```bash
sudo udevadm test --action=add  /sys/class/net/enxacde48001122 2>&1 | grep NM_UNMANAGED   # set
sudo udevadm test --action=move /sys/class/net/enxacde48001122 2>&1 | grep NM_UNMANAGED   # gone
```

## Fix (use both)

```bash
sudo cp 90-t1bridge-ncm-unmanaged.rules /etc/udev/rules.d/    # ACTION!="remove"
sudo cp 99-t1-ibridge-unmanaged.conf /etc/NetworkManager/conf.d/
sudo nmcli connection delete "Wired connection 1"   # the auto-created profile, if present
sudo udevadm control --reload
sudo nmcli general reload conf
nmcli device | grep enxacde                           # → unmanaged
```

The NetworkManager file matches by MAC, which is the same on every T1 Mac.
The interface itself stays up, so the T1 keeps working.
