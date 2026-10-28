"""Liest die Kursseite aus und schreibt kurse.json (nur bei Aenderungen)."""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

NR = re.compile(r"^20\d\d/.+/\d+$")  # Kursnummer, z. B. 2026/FUNK-GL/6
DT = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})")
ORTE = [("Ehingen", "e"), ("Laichingen", "l"), ("Erbach", "r")]  # sonst Ulm = "u"


def parse(lines):
    segs, titles, cur = [], {}, None
    for i, l in enumerate(lines):
        if NR.match(l):
            cur = l
            segs.append((l, []))
            titles.setdefault(l, lines[i - 1] if i else l)
        elif cur:
            segs[-1][1].append(l)
    blocks = {}
    for n, ls in segs:  # Seite enthaelt jeden Kurs doppelt (Desktop/Mobil)
        blocks.setdefault(n, []).extend(ls)
    kurse = []
    for n, ls in blocks.items():
        text = "\n".join(ls)
        termine = sorted({f"{y}-{m}-{d}@{a}-{b}" for d, m, y, a, b in DT.findall(text)})
        if not termine:
            continue
        f = re.search(r"(\d+)\s+Freie Pl", text)
        ort = next((k for name, k in ORTE if name in text), "u")
        kurse.append({
            "t": titles[n], "n": n, "p": ort,
            "f": int(f.group(1)) if f and int(f.group(1)) < 1000 else 0,
            "g": 1 if "auf anfrage" in text.lower() else 0,
            "d": termine,
        })
    kurse.sort(key=lambda k: k["d"][0])
    return kurse


def main():
    import requests
    from bs4 import BeautifulSoup
    r = requests.get(os.environ["KURS_URL"], timeout=30,
                     headers={"User-Agent": "Mozilla/5.0 (Kurskalender)"})
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    text = soup.get_text("\n").replace("\xa0", " ")
    kurse = parse([l.strip() for l in text.splitlines() if l.strip()])
    if not kurse:
        sys.exit("Keine Kurse gefunden - Seitenaufbau geaendert? kurse.json bleibt unveraendert.")
    try:
        alt = json.load(open("kurse.json", encoding="utf-8"))["kurse"]
    except Exception:
        alt = None
    if alt == kurse:
        print("Keine Aenderungen.")
        return
    stand = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M Uhr")
    with open("kurse.json", "w", encoding="utf-8") as fh:
        json.dump({"stand": stand, "kurse": kurse}, fh, ensure_ascii=False, indent=1)
    print(f"{len(kurse)} Kurse gespeichert.")


if __name__ == "__main__":
    main()
