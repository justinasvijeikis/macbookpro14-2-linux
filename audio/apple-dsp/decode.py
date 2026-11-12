import json,struct,sys
f2=lambda i: struct.unpack('<f',struct.pack('<i',i))[0]
d=json.load(open(sys.argv[1]))
sps=d["PathMapRef"][0]["IntSpeaker"]["SignalProcessing"]
for si,sp in enumerate(sps):
  dsp=sp["SoftwareDSP"]
  print("######## SignalProcessing",si)
  for k in sorted([k for k in dsp if k.startswith("DspFunction")], key=lambda x:int(x[11:])):
    f=dsp[k]; n=f["FunctionInfo"]["DspFuncName"]; pi=f.get("ParameterInfo",{})
    src=[(p["SourceFuncInstance"],p["SourcePortIndex"]) for p in f.get("PatchbayInfo",{}).values()]
    print(f"--- {k} {n} in={src}")
    if n=="DspEqualization32":
      for fl in pi.get("Filter",[]):
        print(f"   ch{fl['2']} #{fl['3']} en?{fl['4']} type{fl['5']:>3} f={f2(fl['6']):9.1f} Q={f2(fl['7']):6.3f} g={f2(fl['8']):7.2f}")
    else:
      print("   ", {kk:(round(f2(v),4) if isinstance(v,int) and abs(v)>100000 else v) for kk,v in pi.items()})
