# scalar-wave-viz

Interactive visualizations exploring how scalar waves interact with different materials — including real exotic metals like **Bismuth** and the superheavy synthetic element **Moscovium (Element 115)** — and what a hypothetically stable version of Moscovium might look like.

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/aguacatero/scalar-wave-viz/HEAD?filepath=wave_3d.ipynb)

---

## What this project is about

The core question: *if you place an object made of an exotic or heavy material in the path of a scalar wave, how does it scatter, slow, and bend that wave — and what would change if the material were even more exotic?*

Starting from established physics (wave equations, diamagnetic properties of Bismuth, FDTD simulation), the project extends into speculative territory: what would the wave interaction look like for a **stable** version of Element 115, if the predicted "island of nuclear stability" could be reached?

---

## Notebooks

### `wave_3d.ipynb` — 3D Wave Interaction Simulator
The main visualization. A scalar wave propagates through a 3D volume and hits an object you choose. Watch the wave compress, bend, and scatter in real time.

- **Shapes:** Sphere, Torus (waves pass through the hole), Pyramid, Bismuth Crystal (rhombohedral geometry)
- **Materials:**
  - *Air* — baseline, unobstructed wave
  - *Bismuth* — real diamagnetic metal; measurably slows and bends waves
  - *Element 115 — Moscovium* — superheavy synthetic element; hypothetical near-trapping
  - *Exotic metamaterial* — theoretical near-zero wave speed; maximum interaction
- **Controls:** Play/pause animation, scrub timeline, rotate the 3D scene
- **Physics:** 3D leapfrog FDTD solver, absorbing boundaries (PML), ~10s compute per run

### `mc_stability.ipynb` — Moscovium Nuclear Stability Explorer
Answers the question: *what ion combination would produce a stable (or near-stable) version of Element 115, and what would its wave properties look like?*

- **Half-life chart** — measured Mc-287 through Mc-290 (from NUBASE2020) plus theoretical predictions out to Mc-299, showing the dramatic jump expected near the N=184 shell closure ("island of stability")
- **Synthesis route ladder** — compares five target+beam combinations (Am + Ca variants) and shows exactly how many neutrons each reaction falls short of the island
- **Interactive explorer** — pick a target nucleus and beam, see which Mc isotopes you'd produce, their half-lives, and how they map to wave-simulation parameters
- **Wave connection** — links each Mc isotope back to a wave speed preset in `wave_3d.ipynb`

> Data labels: 🟢 Measured (NUBASE2020) · 🟠 Predicted (WS4/FRDM2012 models) · 🔭 Speculative extrapolation

### `wave_demo.ipynb` — 1D Wave Demos
Introductory 1D simulations: animated E/B-field cosines with sliders, and a scalar wave passing through a Gaussian material barrier.

---

## Quick start

**Run in browser (no install):**
Click the Binder badge above — opens `wave_3d.ipynb` directly.

**Run locally:**
```bash
pip install numpy matplotlib ipywidgets ipympl plotly
jupyter notebook
```
Open `wave_3d.ipynb` or `mc_stability.ipynb`, run all cells, and use the interactive controls.

---

## Key concepts (no physics background required)

| Term | Plain meaning |
|---|---|
| Scalar wave | A wave described by a single value at each point in space — like pressure in sound |
| FDTD | "Finite-Difference Time-Domain" — a method for simulating how waves evolve step by step on a grid |
| Diamagnetic | A material that slightly repels magnetic fields; Bismuth is the strongest natural example |
| Island of stability | A predicted region of the nuclear chart where superheavy elements become dramatically longer-lived due to filled nuclear shells |
| N=184 | The predicted next "magic" neutron number — reaching it in Mc (Z=115) would give Mc-299, estimated half-life ~5 hours vs the current record of 0.65 seconds |
