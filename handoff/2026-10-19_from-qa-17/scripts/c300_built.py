"""QA r17 C300 built hang at the EXPORT hub (r16 P2 method on p_x). Resumable, checkpoint per design.
Usage: python c300_built.py <p1.jsonl> <c300_analytic.jsonl> <out.jsonl> [workers]"""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
sys.path.insert(0, __file__.rsplit("/", 1)[0])


def work(r):
    t0 = time.monotonic(); out = {"id": r["id"]}
    try:
        import p2_built as P2
        from c_common import export_hub
        from fansim.geometry import blade as B
        from fansim.geometry.chord_realisation import loft_chords_for_measured_targets, with_loft_chords, correct_clipped_sections
        p, d = export_hub(P2.params_of(r)); face = float(B._hub_axial_range(p)[0])
        loft = with_loft_chords(p, loft_chords_for_measured_targets(p))
        pr = correct_clipped_sections(loft, p)
        zb, rfb = P2.sec_zmin(pr, B)
        out.update(dh=d, face_x=face, s_bx=face - zb, h_bx=max(0.0, face - zb), h_x=B.blade_hang_below_hub_mm(p))
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
    out["mono_s"] = round(time.monotonic() - t0, 1)
    return out


def main(p1, ana, out, workers=3):
    P1 = {json.loads(l)["id"]: json.loads(l) for l in open(p1)}
    todo_ids = [json.loads(l)["id"] for l in open(ana) if json.loads(l)["h_x"] > 0]
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    todo = [P1[i] for i in todo_ids if i not in done]
    print("selected", len(todo_ids), "todo", len(todo), flush=True); t0 = time.monotonic()
    with ProcessPoolExecutor(int(workers), max_tasks_per_child=1) as ex:
        futs = [ex.submit(work, r) for r in todo]
        for k, f in enumerate(as_completed(futs)):
            rec = f.result()
            with open(out, "a") as fh: fh.write(json.dumps(rec) + "\n")
            print(k + 1, rec["id"], rec.get("error") or (round(rec["h_x"], 2), round(rec["h_bx"], 2)), rec["mono_s"],
                  round(time.monotonic() - t0), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
