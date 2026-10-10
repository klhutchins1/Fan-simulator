"""Build docs/qa/benchmarks/<id>/{geometry.json,curve.csv} from cited numbers (round 6, Task D).
Every number below is copied from the cited source or derived as stated; nothing is tuned."""
import json, csv, math, os, sys
OUT = sys.argv[1]
CFM = 1/2118.88; MMH2O = 9.80665
def V(v, status, note=None):
    d = {"value": v, "status": status}
    if note: d["note"] = note
    return d
def write(fid, geom, rows, cols):
    d = os.path.join(OUT, fid); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "geometry.json"), "w") as f: json.dump(geom, f, indent=1)
    with open(os.path.join(d, "curve.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows: w.writerow(r)

# ---------- LT120: Lin & Tsai 7-blade 120 mm fan, geometry from Tutar & Cam 2025 Table 1 (CC BY) ----------
tbl = [(23.0,18.6,39.9,"4420"),(26.7,21.2,39.7,"4418"),(30.4,23.6,39.5,"4416"),(34.2,26.2,39.3,"4414"),
       (37.9,28.9,38.9,"4412"),(41.6,31.6,38.6,"4410"),(45.3,34.2,38.2,"4408"),(49.1,36.6,37.7,"4406"),
       (52.8,39.1,37.0,"4406"),(56.5,41.6,36.0,"4406")]
st = []
for r,c,a,naca in tbl:
    st.append({"r_mm": V(r,"published"), "chord_mm": V(c,"published"),
               "stagger_deg": V(a,"assumed","published 'setting angle'; assumed measured from the rotation plane (it decreases hub->tip, i.e. normal fan twist)"),
               "max_camber": V(int(naca[0])/100,"derived","NACA "+naca+" first digit"),
               "camber_pos": V(int(naca[1])/10,"derived","NACA "+naca+" second digit"),
               "thickness": V(int(naca[2:])/100,"derived","NACA "+naca+" last two digits")})
g = {"fan_id":"lt120","full_geometry":True,
     "n_blades":V(7,"published"),"hub_radius_mm":V(25.0,"published","hub diameter 50 mm"),
     "tip_radius_mm":V(60.0,"published","rotor diameter 120 mm"),"rpm":V(2000,"published"),
     "tip_gap_mm":V(0.5,"assumed","not reported; fansim default"),
     "section_family":V("naca","published","NACA 4-digit sections"),
     "stations":st,
     "bem_mapping":"r_frac=(r-hub)/(tip-hub); segment 1 (r=23.0 < hub 25.0) placed at r_frac 0; segment 10 values reused at r_frac 1 (no extrapolation)",
     "source_note":"Table radii 23.0-56.5 mm do not span the stated 25-60 mm annulus; the paper gives no explanation."}
rows=[]
for q,p in [(8.02,34.01),(32.01,17.14),(40.00,14.69),(60.00,13.71),(84.00,6.85)]:
    rows.append([f"{q*CFM:.6f}",f"{p:.2f}",2000,"","","static"])
write("lt120",g,rows,["q_m3s","dp_pa","rpm","power_w","eta","pressure_type"])

# ---------- NV150: Novakovic et al. 2024 baseline fan (CC BY-NC-ND) ----------
prof=[(28,37.4,0,36,3.4,2.0),(43,18.7,2,37,2.0,1.8),(59,12.7,1,34,1.8,1.6),(75,9.7,1,33,1.4,1.4)]
st=[]
for R,b,al,L,f,t in prof:
    st.append({"r_mm":V(R,"derived","Table 1 column 'R'; read as station radius (28 = hub, 75 = tip); the text calls R the arc radius, but an arc radius would be (L^2/4+f^2)/(2f), which does not match"),
               "chord_mm":V(L,"published"),
               "stagger_deg":V(round(b+al,2),"derived",f"beta_inf {b} + alpha {al} (beta from the circumferential direction, Eck convention; checked against the design-point flow angle at the tip)"),
               "max_camber":V(round(f/L,4),"derived",f"sagitta {f} mm / chord"),
               "camber_pos":V(0.5,"derived","circular arc"),
               "thickness":V(round(t/L,4),"derived",f"t {t} mm / chord (constant-thickness arc plate)")})
g={"fan_id":"nv150","full_geometry":True,"n_blades":V(6,"published"),
   "hub_radius_mm":V(28.0,"published","hub diameter 56 mm"),"tip_radius_mm":V(75.0,"published","outer diameter 150 mm"),
   "rpm":V(3500,"published"),"tip_gap_mm":V(2.0,"published"),"section_family":V("plate","assumed","3D-printed circular-arc plate; fansim 'plate' is the closest family"),
   "stations":st,"bem_mapping":"r_frac=(r-28)/(75-28)",
   "design_point":{"Q_m3h":V(245,"published"),"dpt_pa":V(76,"published"),"phi":V(0.14,"published"),"psi_t":V(0.17,"published")}}
phi=[0.0211,0.0450,0.0648,0.0806,0.0925,0.1010,0.1089,0.1168,0.1240,0.1287,0.1347,0.1388,0.1423,0.1501,0.1608,0.1649]
psi=[0.3497,0.3033,0.2627,0.2267,0.1990,0.1745,0.1565,0.1455,0.1365,0.1275,0.1217,0.1159,0.1114,0.0998,0.0824,0.0753]
eta=[14.6,29.4,38.6,46.0,48.2,49.1,49.5,50.0,50.2,49.7,49.7,50.9,47.7,45.6,44.9,43.8]
u=math.pi*0.15*3500/60; A=math.pi*0.15**2/4; rho=1.2
rows=[]
for a,b,e in zip(phi,psi,eta):
    q=a*A*u; dp=b*0.5*rho*u*u
    rows.append([f"{q:.5f}",f"{dp:.1f}",3500,f"{q*dp/(e/100):.2f}",f"{e/100:.3f}","total"])
write("nv150",g,rows,["q_m3s","dp_pa","rpm","power_w","eta","pressure_type"])

# ---------- NF-A12x25: repo Stock recipe (fit to the close-reference STL) + Noctua spec endpoints ----------
g={"fan_id":"nf-a12x25","full_geometry":True,
   "geometry_source":V("config/problems/a12x25_reference.yaml @ 31228d0","derived","stations fitted to validation/reference/a12x25_impeller.stl (user-provided, not OEM CAD); fit tolerance from the yaml header: stagger 1.5 deg, chord 3%, camber 0.005, t/c 10%"),
   "n_blades":V(9,"published","Noctua; also in the repo recipe"),"hub_radius_mm":V(21.5,"derived","repo recipe"),
   "tip_radius_mm":V(54.5,"derived","repo recipe"),"rpm":V(2000,"published","Noctua max speed"),
   "tip_gap_mm":V(0.5,"published","per docs/validation/a12x25_pq_report.md")}
rows=[[f"{0:.6f}",f"{2.34*MMH2O:.2f}",2000,"","","static"],[f"{60.09*CFM:.6f}",f"{0:.2f}",2000,"","","static"]]
write("nf-a12x25",g,rows,["q_m3s","dp_pa","rpm","power_w","eta","pressure_type"])

# ---------- Delta curve_only (spec-sheet endpoints) ----------
delta={"delta-afb0412hhb":(40,8300,11.48,9.13,1.56,"JUL.26.2004"),
       "delta-afb0612hhb":(60,4500,17.30,4.97,1.44,"SEP.07.2005"),
       "delta-afb0812sh":(80,4000,46.62,6.76,4.08,"FEB.11.2004"),
       "delta-afb0912vh":(92,3800,67.80,7.67,4.80,"JUL.14.2006"),
       "delta-afb1212sh":(120,3400,113.11,10.92,6.36,"APR.19.2004")}
for fid,(size,rpm,cfm,mm,pin,date) in delta.items():
    g={"fan_id":fid,"full_geometry":False,"curve_only":True,
       "frame_size_mm":V(size,"published","model family size, not the rotor diameter"),
       "rpm":V(rpm,"published","rated speed (REF.) at 12 V"),"input_power_w":V(pin,"published","rated electrical input at 12 V"),
       "n_blades":V(None,"unknown"),"hub_radius_mm":V(None,"unknown"),"tip_radius_mm":V(None,"unknown")}
    rows=[[f"{0:.6f}",f"{mm*MMH2O:.2f}",rpm,"","","static"],[f"{cfm*CFM:.6f}",f"{0:.2f}",rpm,"","","static"]]
    write(fid,g,rows,["q_m3s","dp_pa","rpm","power_w","eta","pressure_type"])
print("ok")
