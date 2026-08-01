#!/usr/bin/env python3
"""
VENTFALL — original sound pack generator.

Every sample here is synthesized from oscillators and filtered noise.
No sampled or third-party audio is used at any point.
"""
import numpy as np, os
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100
rng = np.random.default_rng(20260731)

def t(d):            return np.linspace(0, d, int(SR*d), endpoint=False)
def noise(d):        return rng.uniform(-1, 1, int(SR*d))
def silence(d):      return np.zeros(int(SR*d))

def env(x, a=.005, d=.05, s=.7, r=.15, sus=None):
    """ADSR over the length of x."""
    n = len(x); sus = sus if sus is not None else max(0, n/SR - a - d - r)
    seg = [np.linspace(0,1,max(1,int(SR*a))),
           np.linspace(1,s,max(1,int(SR*d))),
           np.full(max(0,int(SR*sus)), s),
           np.linspace(s,0,max(1,int(SR*r)))]
    e = np.concatenate(seg)
    return x * (np.resize(e, n) if len(e) < n else e[:n])

def decay(x, k=12):  return x * np.exp(-k*np.linspace(0,len(x)/SR,len(x)))

def osc(f, d, kind="sine", detune=0.0):
    tt = t(d)
    if callable(f): ph = 2*np.pi*np.cumsum(np.asarray(f(tt)))/SR
    else:           ph = 2*np.pi*f*tt
    ph = ph*(1+detune)
    if kind=="sine": return np.sin(ph)
    if kind=="tri":  return 2/np.pi*np.arcsin(np.sin(ph))
    if kind=="saw":  return 2*((ph/(2*np.pi))%1)-1
    if kind=="sq":   return np.sign(np.sin(ph))
    raise ValueError(kind)

def sweep(f0, f1, d, kind="sine"):
    tt = t(d); f = f0*(f1/f0)**(tt/max(d,1e-6))
    return osc(lambda _: f, d, kind)

def bp(x, lo, hi, order=2):
    ny = SR/2
    lo = max(20, min(lo, ny-100)); hi = max(lo+50, min(hi, ny-50))
    return sosfilt(butter(order, [lo/ny, hi/ny], btype="band", output="sos"), x)

def lp(x, fc, order=2):
    ny = SR/2
    return sosfilt(butter(order, min(fc,ny-50)/ny, btype="low", output="sos"), x)

def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts: out[:len(p)] += p
    return out

def norm(x, peak=.82):
    m = np.max(np.abs(x))
    return x*(peak/m) if m > 0 else x

def fade(x, ms=6):
    n = int(SR*ms/1000); n = min(n, len(x)//2)
    if n < 2: return x
    x = x.copy(); x[:n] *= np.linspace(0,1,n); x[-n:] *= np.linspace(1,0,n)
    return x

def reverb(x, dry=.82, taps=((.031,.30),(.052,.22),(.079,.15),(.113,.09))):
    """Cheap early-reflection cluster — gives the sense of a big flooded room."""
    out = x*dry
    for dt, g in taps:
        d = int(SR*dt); pad = np.concatenate([np.zeros(d), lp(x, 3000)*g])
        out = mix(out, pad)
    return out

# ------------------------------------------------------------------ effects
def s_select():
    a = decay(osc(880,.09,"tri"), 26); b = decay(sweep(880,1180,.09,"tri"), 22)
    return norm(mix(a*.5, b*.7), .55)

def s_order():
    return norm(decay(sweep(520,700,.08,"sq"), 30)*.6, .5)

def s_attack_order():
    return norm(decay(sweep(300,180,.16,"saw"), 16)*.7, .62)

def s_build_place():
    thud = decay(sweep(190,110,.22,"sq"), 14)
    clank = decay(bp(noise(.12), 1400, 4200), 34)*.5
    return norm(mix(thud*.8, clank), .7)

def s_build_complete():
    parts = []
    for i, f in enumerate((523.25, 659.25, 880.0)):
        d = .34; s = decay(mix(osc(f,d,"tri"), osc(f*2,d,"sine")*.28), 9)
        parts.append(np.concatenate([silence(i*.085), s*.55]))
    return norm(reverb(mix(*parts)), .72)

def s_weapon_light():
    crack = decay(bp(noise(.09), 1700, 6000), 46)
    body  = decay(sweep(430,150,.08,"sq"), 40)
    return norm(mix(crack*.75, body*.55), .68)

def s_weapon_heavy():
    boom = decay(sweep(210,62,.20,"saw"), 17)
    air  = decay(bp(noise(.19), 700, 2600), 20)
    return norm(mix(boom*.8, air*.6), .78)

def s_impact():
    return norm(decay(bp(noise(.07), 2000, 7000), 55)*.75, .6)

def s_explosion_small():
    body = decay(sweep(300,70,.42,"sine"), 11)
    grit = decay(lp(noise(.38), 1800), 9)
    return norm(reverb(mix(body*.75, grit*.85)), .84)

def s_explosion_large():
    sub  = decay(sweep(120,26,.95,"sine"), 4.2)
    body = decay(lp(noise(.85), 900), 4.6)
    crack= decay(bp(noise(.30), 900, 3800), 12)*.55
    return norm(reverb(mix(sub*.95, body*.9, crack), dry=.75), .92)

def s_ore_deposit():
    a = decay(sweep(1050,1500,.07,"sine"), 34)
    b = decay(osc(2100,.05,"sine"), 46)*.3
    return norm(mix(a*.6, b), .5)

def s_sonar_ping():
    d = .95; tone = osc(1420, d, "sine")*np.exp(-3.1*t(d))
    return norm(reverb(tone*.5, dry=.55), .58)

def s_alarm():
    out = silence(.44)
    for off in (0.0, .20):
        s = decay(sweep(770,520,.17,"sq"), 12)*.6
        p = np.concatenate([silence(off), s])
        out = mix(out, p)
    return norm(out, .74)

def s_denied():
    return norm(decay(sweep(200,140,.14,"sq"), 20)*.65, .55)

def s_ui_click():
    return norm(decay(osc(1300,.03,"sq"), 90)*.45, .4)

def s_victory():
    out = silence(1.9)
    for i, f in enumerate((392.0, 523.25, 659.25, 783.99)):
        d = .62; v = decay(mix(osc(f,d,"tri"), osc(f*2,d,"sine")*.22, osc(f*.5,d,"sine")*.3), 4.3)
        out = mix(out, np.concatenate([silence(i*.15), v*.42]))
    return norm(reverb(out), .8)

def s_defeat():
    out = silence(2.4)
    for i, f in enumerate((330.0, 262.0, 196.0, 147.0)):
        d = .85; v = decay(mix(osc(f,d,"saw")*.5, osc(f*.995,d,"tri")*.5), 3.2)
        out = mix(out, np.concatenate([silence(i*.20), lp(v,1500)*.45]))
    return norm(reverb(out, dry=.7), .8)

def s_ambient_loop():
    """8 s seamless bed: sub swell + filtered water wash + distant vent knocks."""
    D = 8.0; n = int(SR*D); tt = t(D)
    # loop-safe LFOs use whole cycles across D
    sub  = osc(41, D, "sine") * (.55 + .45*np.sin(2*np.pi*tt/D))
    sub2 = osc(61.5, D, "sine")*.25*(.5+.5*np.sin(4*np.pi*tt/D))
    wash = lp(noise(D), 190) * (.6 + .4*np.sin(2*np.pi*2*tt/D))
    knocks = np.zeros(n)
    for pos in (1.3, 3.1, 4.4, 6.7):
        k = decay(lp(noise(.16), 700), 26)*.30
        i = int(SR*pos); k = k[:max(0, n-i)]
        knocks[i:i+len(k)] += k
    bed = mix(sub*.42, sub2, wash*.5, knocks)
    # crossfade the tail into the head so it loops without a seam
    x = int(SR*0.5)
    bed[:x] = bed[:x]*np.linspace(0,1,x) + bed[-x:]*np.linspace(1,0,x)
    return norm(bed[:n-x], .55)

EFFECTS = [
    ("ui_select",          s_select,          "Unit selection blip"),
    ("ui_click",           s_ui_click,        "Generic button click"),
    ("ui_denied",          s_denied,          "Invalid / unaffordable action"),
    ("order_move",         s_order,           "Move order acknowledged"),
    ("order_attack",       s_attack_order,    "Attack order acknowledged"),
    ("build_place",        s_build_place,     "Structure footprint placed"),
    ("build_complete",     s_build_complete,  "Construction finished"),
    ("weapon_light",       s_weapon_light,    "Light rapid weapon"),
    ("weapon_heavy",       s_weapon_heavy,    "Heavy turret weapon"),
    ("impact",             s_impact,          "Projectile impact"),
    ("explosion_small",    s_explosion_small, "Unit destroyed"),
    ("explosion_large",    s_explosion_large, "Structure destroyed"),
    ("ore_deposit",        s_ore_deposit,     "Resource delivered"),
    ("sonar_ping",         s_sonar_ping,      "Minimap sonar sweep"),
    ("alarm_underattack",  s_alarm,           "Base under attack"),
    ("sting_victory",      s_victory,         "Victory sting"),
    ("sting_defeat",       s_defeat,          "Defeat sting"),
    ("ambient_loop",       s_ambient_loop,    "Seamless 7.5 s underwater bed"),
]

# ---------------------------------------------------------------- advisor cues
# Short filtered-comms tones. The era's character came from narrowband
# radio filtering (roughly 500-2800 Hz) plus a little bit-crush.

def comms(x, lo=520, hi=2700, crush=0):
    """Squeeze a signal into a radio band, optionally bit-crushed."""
    y = bp(x, lo, hi, order=3)
    if crush:
        step = 2.0/(2**crush)
        y = np.round(y/step)*step
    return y

def blip(f, d, kind="sq", k=18):
    return decay(osc(f, d, kind), k)

def s_alert_resources():          # "insufficient resources"
    a = mix(blip(760,.09), blip(560,.09)*0)
    b = np.concatenate([a, silence(.04), decay(osc(520,.13,"sq"),14)])
    return comms(b, 480, 2400, crush=6)*.9

def s_alert_capacity():           # "additional crew berths required"
    seq = [ (640,.08), (640,.08), (470,.16) ]
    out = []
    for f,d in seq:
        out += [decay(osc(f,d,"sq"),16), silence(.035)]
    return comms(np.concatenate(out), 500, 2500, crush=6)*.9

def s_alert_construction():       # "construction complete"
    seq = [(523,.10),(659,.10),(784,.20)]
    out = []
    for f,d in seq:
        out += [decay(osc(f,d,"tri"),9), silence(.02)]
    return comms(np.concatenate(out), 420, 3000, crush=0)*.95

def s_alert_unit_ready():         # "unit ready"
    a = decay(sweep(620, 940, .13, "tri"), 11)
    b = decay(osc(940,.10,"tri"), 13)
    return comms(np.concatenate([a, silence(.02), b]), 460, 2900)*.95

def s_alert_research():           # "upgrade complete"
    a = decay(sweep(400, 1000, .30, "tri"), 6)
    h = decay(sweep(800, 2000, .30, "sine"), 7)*.4
    return comms(mix(a,h), 420, 3200)*.95

def s_alert_lost():               # "we've lost a structure"
    a = decay(sweep(520, 240, .34, "saw"), 7)
    return comms(a, 400, 2200, crush=5)*.95

def s_ack_yes():                  # affirmative chirp
    return comms(decay(sweep(700,1080,.09,"tri"),16), 520, 2800, crush=5)*.85

def s_ack_move():                 # movement acknowledgment
    a = decay(osc(880,.06,"tri"),20); b = decay(osc(1180,.06,"tri"),20)
    return comms(np.concatenate([a, silence(.015), b]), 520, 3000, crush=5)*.8

def s_ack_attack():               # attack acknowledgment
    a = decay(osc(420,.08,"saw"),15); b = decay(osc(300,.11,"saw"),13)
    return comms(np.concatenate([a, silence(.02), b]), 400, 2400, crush=5)*.85

def s_ack_build():                # worker accepts a build order
    return comms(decay(sweep(520,760,.11,"sq"),14), 500, 2600, crush=6)*.8

def s_weapon_missile():           # launcher
    body = decay(bp(noise(.34), 300, 2600, order=3), 7)
    whine = decay(sweep(1400, 320, .34, "saw"), 5)*.35
    return mix(body, whine)*.95

def s_weapon_energy():            # beam / plasma
    core = decay(sweep(1800, 420, .22, "sq"), 9)*.5
    air  = decay(bp(noise(.22), 900, 5200, order=3), 12)*.6
    return mix(core, air)

def s_shield_hit():
    ring = decay(osc(1650,.20,"sine"), 11)*.5
    tick = decay(bp(noise(.20), 1800, 6000, order=3), 22)*.5
    return mix(ring, tick)

def s_repair_loop():              # short loopable repair/weld bed
    d = 1.2
    base = bp(noise(d), 700, 4200, order=2)
    am = .55 + .45*np.sign(np.sin(2*np.pi*11*t(d)))
    y = base*am*.5
    n = int(SR*.06)
    y[:n] *= np.linspace(0,1,n); y[-n:] *= np.linspace(1,0,n)
    return y

EXTRA = [
    ("alert_resources",     s_alert_resources,    "Insufficient resources"),
    ("alert_capacity",      s_alert_capacity,     "Crew capacity reached"),
    ("alert_construction",  s_alert_construction, "Construction complete"),
    ("alert_unit_ready",    s_alert_unit_ready,   "Unit ready"),
    ("alert_research",      s_alert_research,     "Upgrade complete"),
    ("alert_lost",          s_alert_lost,         "Structure lost"),
    ("ack_yes",             s_ack_yes,            "Generic affirmative"),
    ("ack_move",            s_ack_move,           "Move order acknowledged"),
    ("ack_attack",          s_ack_attack,         "Attack order acknowledged"),
    ("ack_build",           s_ack_build,          "Build order acknowledged"),
    ("weapon_missile",      s_weapon_missile,     "Missile / launcher"),
    ("weapon_energy",       s_weapon_energy,      "Energy weapon"),
    ("shield_hit",          s_shield_hit,         "Shield / armour deflect"),
    ("repair_loop",         s_repair_loop,        "Loopable repair / weld bed"),
]
EFFECTS = EFFECTS + EXTRA


def main():
    out = os.environ.get("PACK_OUT","/home/claude/pack")
    wd, md = os.path.join(out,"wav"), os.path.join(out,"mp3")
    os.makedirs(wd, exist_ok=True); os.makedirs(md, exist_ok=True)
    rows = []
    for name, fn, desc in EFFECTS:
        a = fade(norm(fn()))
        p = os.path.join(wd, name+".wav")
        wavfile.write(p, SR, (a*32767).astype(np.int16))
        rows.append((name, desc, len(a)/SR, os.path.getsize(p)))
        print(f"  {name:22s} {len(a)/SR:5.2f}s")
    import json
    json.dump([{"name":n,"description":d,"seconds":round(s,3)} for n,d,s,_ in rows],
              open(os.path.join(out,"_manifest.json"),"w"), indent=2)
    print(f"\n{len(rows)} files written")

if __name__ == "__main__":
    main()
