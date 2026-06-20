# Sophia

> _**sophia** / *n.* / (Greek: *σοφία*)_ <sub>so‧phi‧a</sub>
> 1. _a female given name from Ancient Greek_
> 2. _wisdom_

**Sophia** is a chess engine written in Python and compiled to native code via Cython. The core hot paths are compiled C extensions, giving performance comparable to compiled engines while keeping the codebase readable. It communicates over the standard UCI protocol.

---

<p align="center">
  <a href="https://lichess.org/@/sxphia">
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Flichess.org%2Fapi%2Fuser%2Fsxphia&query=%24.perfs.bullet.rating&label=Bullet&color=8C8FBA&labelColor=1A1E23&style=flat-square&logo=lichess&logoColor=white" alt="Bullet Elo">
  </a>
  <a href="https://lichess.org/@/sxphia">
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Flichess.org%2Fapi%2Fuser%2Fsxphia&query=%24.perfs.blitz.rating&label=Blitz&color=8C8FBA&labelColor=1A1E23&style=flat-square&logo=lichess&logoColor=white" alt="Blitz Elo">
  </a>
  <a href="https://lichess.org/@/sxphia">
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Flichess.org%2Fapi%2Fuser%2Fsxphia&query=%24.perfs.rapid.rating&label=Rapid&color=8C8FBA&labelColor=1A1E23&style=flat-square&logo=lichess&logoColor=white" alt="Rapid Elo">
  </a>
</p>

<p align="center">
  <a href="https://lichess.org/@/sxphia">
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Flichess.org%2Fapi%2Fusers%2Fstatus%3Fids%3Dsxphia&query=%24%5B0%5D.online&label=Active&color=F58D55&labelColor=1A1E23&style=flat-square" alt="Online Status">
  </a>
</p>

---

## Requirements

- Python 3.11+
- GCC or Clang (for compiling the Cython extensions)
- Linux

## Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install cython setuptools

# Compile the engine
cd sophia
python setup.py build_ext --inplace
cd ..
```

## Running

Point your UCI GUI at `sophia/engine.sh`.

To run directly from the terminal in UCI mode:

```bash
source venv/bin/activate
./sophia/engine.sh
```

After compilation, the engine runs as native machine code — no interpreter overhead in the search.

## Tournament (self-play)

```bash
source venv/bin/activate
python tourney.py
```

Edit `tourney.py` to configure time controls, number of games, and which engines to pit against each other. The tournament can run with a pygame GUI or in headless TUI mode.
