"""Approximate read-off of Tutar & Cam 2025 Figs 8/9 (CC BY 4.0) at the 5 measured flows. Report-only; figures cited, not stored in repo."""
from PIL import Image; import numpy as np, sys
def run(f, colours):
    im=np.array(Image.open(f).convert('RGB')).astype(int); R,G,B=im[...,0],im[...,1],im[...,2]
    blk=(R<60)&(G<60)&(B<60)
    rows=blk.sum(1); cols=blk.sum(0)
    # plot frame: longest black rows/cols
    yax=int(np.argmax(rows)); xax=int(np.argmax(cols))
    xs=np.where(blk[yax])[0]; ys=np.where(blk[:,xax])[0]
    xl,xr=xax,xs.max(); ytop,ybot=ys.min(),yax  # axes run 0..90 cfm and 0..40 Pa
    # frame: x 0..90 cfm, y 0..40 Pa
    X=lambda c: xl+(xr-xl)*c/90.0; P=lambda y:(ybot-y)/(ybot-ytop)*40.0
    out={}
    for name,m in colours.items():
        mask=m(R,G,B); res=[]
        for c in [8,32,40,60,84]:
            x=int(round(X(c))); sub=mask[ytop+5:ybot-5, x-20:x+21]
            ys,xs=np.nonzero(sub)
            res.append(None if len(ys)<30 else round(P(ytop+5+np.median(ys)),2))
        out[name]=res
    print(f, 'frame', (xl,xr,ytop,ybot)); [print(' ',k,v) for k,v in out.items()]
red=lambda R,G,B:(R>200)&(G<60)&(B<60); blue=lambda R,G,B:(B>200)&(R<80)&(G<80)
green=lambda R,G,B:(G>180)&(R<80)&(B<80); black=lambda R,G,B:(R<40)&(G<40)&(B<40)
run(sys.argv[1]+'/g008.png',{'3M_blue':blue,'3.77M_green':green,'exp_black(incl.curve)':black})
run(sys.argv[1]+'/g009.png',{'RNG_red':red,'SST_blue':blue})

# Inverse read: flow at 13.71 Pa on the RNG / 3.77M CFD curves (linear between the 40 and 60 cfm markers),
# with a +-0.5 Pa read-off shift. Values typed from the run above (figure read is approximate).
def q_at(p, pts):
    for (q1, p1), (q2, p2) in zip(pts, pts[1:]):
        if (p1 - p) * (p2 - p) <= 0 and p1 != p2:
            return q1 + (p1 - p) / (p1 - p2) * (q2 - q1)
    return None
for name, pts in {"RNG_fig9": [(8, 34.89), (32, 15.61), (40, 13.79), (60, 12.67), (84, 6.08)],
                  "3.77M_fig8": [(8, 34.98), (32, 16.36), (40, 13.86), (60, 12.72), (84, 6.0)]}.items():
    print(name, {sh: (lambda r: None if r is None else round(r, 1))(q_at(13.71, [(q, p + sh) for q, p in pts])) for sh in (-0.5, 0.0, 0.5)},
          "Q@6.85:", round(q_at(6.85, pts), 1))
