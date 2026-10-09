"""Tyler-Sofrin rotor-strut interaction modes m = n*B - k*V (cheap prototype for noise lead #1).
For each blade-pass harmonic n, the lowest |m| that a blade/strut pair can excite decides how well
the tone escapes a compact (short-duct) PC fan: |m|=0 -> net axial-force dipole, |m|=1 -> net
side-force dipole (both radiate well); |m|>=2 -> cancels to order (kR/2)^(|m|-1)/|m|! (estimate)."""
import math, sys
C0, R, RPM = 343.0, 0.060, 2000.0
def modes(B, V, n, kmax=60):
    return sorted(((abs(n * B - k * V), k) for k in range(-kmax, kmax + 1)), key=lambda t: (t[0], abs(t[1])))
def supp_db(m, kR):
    if m <= 1: return 0.0
    return 20 * math.log10((kR / 2) ** (m - 1) / math.factorial(m))
def row(B, V, nmax=4):
    out = []
    for n in range(1, nmax + 1):
        m, k = modes(B, V, n)[0]
        kR = 2 * math.pi * n * B * RPM / 60 / C0 * R
        out.append(f"{m} (k={k}, {supp_db(m, kR):.0f} dB)" if m > 1 else (f"**{m}** (k={k}, axial dipole)" if m == 0 else f"**{m}** (k={k}, side dipole)"))
    return out
if __name__ == "__main__":
    print(f"rpm {RPM:.0f}, R {R*1e3:.0f} mm, BPF(B=9) = {9*RPM/60:.0f} Hz, kR at BPF = {2*math.pi*9*RPM/60/C0*R:.2f}\n")
    print("| B blades | V struts | n=1 (BPF) | n=2 | n=3 | n=4 |\n|---|---|---|---|---|---|")
    for B in (7, 9, 11):
        for V in (3, 4, 5, 6, 7):
            print(f"| {B} | {V} | " + " | ".join(row(B, V)) + " |")
