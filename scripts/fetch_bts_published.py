import re, subprocess, sys, json
# Month links on the BTS page: Jan 2026 = FHGEG, Apr 2026 = FHGEJ, Sep 2026 = FHGFE (letters are shifted digits).
def page(code):
    u = f"https://www.transtats.bts.gov/OT_Delay/ot_delaycause1.asp?qv52ynB=qn6n&20=E&2r4v1qs41z={code}&2r4v1q61={code}"
    s = subprocess.run(["curl", "-s", "-m", "60", "-A", "Mozilla/5.0", u], capture_output=True, text=True).stdout
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", s, flags=re.S)))
    m = re.search(r"National \(([A-Za-z]+, \d{4})\)", t)
    vals = dict((k, (int(a.replace(",", "")), float(b), c)) for k, a, b, c in re.findall(r"(On Time|Air Carrier Delay|Weather Delay|National Aviation System Delay|Security Delay|Aircraft Arriving Late|Cancelled|Diverted|Total Operations) ([\d,]+) ([\d.]+)% ([\d,]+|N/A)", t))
    return (m.group(1) if m else None), vals
def enc(n, dE): return "".join(chr(ord("E") + int(d) - dE) for d in str(n))
jan = "FHGEG"
for dE in range(0, 6):
    n_jan = int("".join(str(ord(ch) - ord("E") + dE) for ch in jan))
    code = enc(n_jan - 3, dE)
    if any(not "A" <= ch <= "Z" for ch in code): continue
    label, v = page(code)
    print(dE, n_jan, code, label)
    if label == "October, 2025":
        out = {}
        for k in range(-3, 9):
            lab, vv = page(enc(n_jan + k, dE)); out[lab] = vv; print(lab, vv.get("On Time"), vv.get("Total Operations"))
        json.dump(out, open(sys.argv[1], "w"), indent=1); break
