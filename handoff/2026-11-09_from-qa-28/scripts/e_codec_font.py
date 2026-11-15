"""r28 E8 / E9b / E10 (PREREG f208f30), CAD-free. Usage: python e_codec_font.py <out.json>"""
import itertools, json, random, sys
from fansim.manufacturability import print_id as P
R = {}
font = set(P._FONT)
R["E8_font_eq_check_alphabet"] = font == set(P.CHECK_ALPHABET)
R["E8_font_extra_or_missing"] = sorted(font ^ set(P.CHECK_ALPHABET))
R["E8_no_ILO_glyph"] = all(P.glyph_strokes(c) == () for c in "ILO")
R["E8_crockford_no_ILOU"] = not any(c in P.CROCKFORD for c in "ILOU") and len(P.CROCKFORD) == 32
rng = random.Random(28)
ids = []
for _ in range(2000):
    b = P._random_body(rng=rng); ids.append(b + P.check_digit(b))
R["E8_ids_body_crockford"] = all(all(c in P.CROCKFORD for c in i[:4]) for i in ids)
R["E8_ids_verify"] = all(P.verify_print_id(i) for i in ids)
R["E8_ids_verify_lowercase"] = all(P.verify_print_id(i.lower()) for i in ids if not any(c in "U" for c in i))
R["E8_normalize"] = {s: P.normalize_read(s) for s in ("il0o", "ILOU", " k7wb2 ")}
sub_total = sub_caught = tr_total = tr_caught = 0
for i in ids[:200]:
    for k in range(5):
        alpha = P.CROCKFORD if k < 4 else P.CHECK_ALPHABET
        for c in alpha:
            if c == i[k]: continue
            j = i[:k] + c + i[k+1:]; sub_total += 1; sub_caught += not P.verify_print_id(j)
    for k in range(4):
        if i[k] != i[k+1]:
            j = i[:k] + i[k+1] + i[k] + i[k+2:]; tr_total += 1; tr_caught += not P.verify_print_id(j)
R["E8_single_substitution_caught"] = f"{sub_caught}/{sub_total}"
R["E8_adjacent_transposition_caught"] = f"{tr_caught}/{tr_total}"
# ids whose check char is one of *~$=U (needs the extended glyphs) — share
R["E8_check_char_extended_share"] = round(sum(i[4] in "*~$=U" for i in ids) / len(ids), 4)
# E9b: identical / near-identical stroke sets
def key(c): return frozenset(tuple(round(v, 3) for v in s) for s in P.glyph_strokes(c))
pairs_same, pairs_near = [], []
for a, b in itertools.combinations(P.CHECK_ALPHABET, 2):
    ka, kb = key(a), key(b)
    if ka == kb: pairs_same.append(a + b)
    elif len(ka ^ kb) <= 1: pairs_near.append(a + b + f" (differ by {[s for s in ka ^ kb]})")
R["E9b_identical_pairs"] = pairs_same; R["E9b_one_stroke_apart"] = pairs_near
# 6 vs G specifically, and S vs 5 overlap
R["E9b_6_vs_G"] = {"6": sorted(key("6")), "G": sorted(key("G"))}
# E10: silent no-op paths
R["E10_hub_can_take_mark"] = {r: P.hub_can_take_mark(r) for r in (15.0, 15.69, 15.7, 21.5)}
R["E10_strokes_len"] = {c: len(P.mark_strokes_xy(c)) for c in ("K7WB2", "K7WB", "K7WB2X", "K7-WB", "k7wb2", "OOOOO")}
json.dump(R, open(sys.argv[1], "w"), indent=1); print(json.dumps(R, indent=1))
