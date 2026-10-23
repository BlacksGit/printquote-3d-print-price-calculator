import re, math, os

def hms(s):
    t = 0
    for n, u in re.findall(r'(\d+)\s*([dhms])', s):
        t += int(n) * {'d': 86400, 'h': 3600, 'm': 60, 's': 1}[u]
    return t

def read_gcode(path):
    """Return grams, seconds read from slicer comments (OrcaSlicer, PrusaSlicer, Bambu Studio, Cura)."""
    head = tail = ''
    with open(path, 'r', errors='ignore') as f:
        head = ''.join(next(f, '') for _ in range(400))
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        f.seek(max(0, size - 60000))
        tail = f.read().decode('utf-8', 'ignore')
    text = head + '\n' + tail
    grams = secs = mm = None
    m = re.search(r';\s*(?:total )?filament (?:used|weight) \[g\]\s*[=:]\s*([\d.,]+)', text, re.I)
    if m:
        grams = sum(float(x) for x in m.group(1).split(',') if x)
    m = re.search(r';\s*filament used \[mm\]\s*=\s*([\d.,]+)', text, re.I)
    if m:
        mm = sum(float(x) for x in m.group(1).split(',') if x)
    m = re.search(r';\s*(?:total estimated time|estimated printing time[^=]*)\s*[=:]\s*([0-9dhms ]+)', text, re.I)
    if m:
        secs = hms(m.group(1))
    if secs is None:
        m = re.search(r';\s*TIME:\s*(\d+)', text)
        if m:
            secs = int(m.group(1))
    if grams is None:
        m = re.search(r';\s*Filament used:\s*([\d.]+)\s*m', text)
        if m:
            mm = float(m.group(1)) * 1000
    return grams, secs, mm

def grams_from_mm(mm, diameter=1.75, density=1.24):
    r = diameter / 2 / 10
    return math.pi * r * r * (mm / 10) * density

def quote(grams, secs, c):
    hours = secs / 3600
    filament = grams / 1000 * c['spool_price'] * c['waste']
    power = hours * c['watts'] / 1000 * c['kwh_price']
    wear = hours * c['machine_hour']
    labor = c['labor_minutes'] / 60 * c['labor_rate']
    cost = filament + power + wear + labor
    cost *= 1 + c['failure_pct'] / 100
    price = cost * (1 + c['markup_pct'] / 100)
    fee = c['fee_pct'] / 100
    if fee:
        price = (price + c['fee_flat']) / (1 - fee)
    return {'filament': filament, 'power': power, 'wear': wear, 'labor': labor, 'cost': cost, 'price': price}

DEFAULTS = {'spool_price': 20.0, 'waste': 1.05, 'watts': 120.0, 'kwh_price': 0.15, 'machine_hour': 0.30,
            'labor_minutes': 10.0, 'labor_rate': 15.0, 'failure_pct': 8.0, 'markup_pct': 100.0,
            'fee_pct': 6.5, 'fee_flat': 0.45}
