import json,sys
for fn in sys.argv[1:]:
    print("=====",fn)
    for s in json.load(open(fn)):
        print("--",s["scenario"],"start:",{k:s["start"][k] for k in("fan_model","material","preset","refine_op","parent","selected")})
        for u in s["used_by_run"]: print("   used:",{k:v for k,v in u.items() if k!="t"})
        for d in s["saved_new"]+s.get("saved_watch",[]): print("   saved:",{k:v for k,v in d.items() if k!="run_used"})
        print("   after:",s["after"])
