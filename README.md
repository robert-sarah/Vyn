# Vyn — High-performance systems language

**Philosophy:** Native speed, hot reload, web + AI + DB built-in.

## Install

```bash
pip install -r requirements.txt
```

## Commands

```bash
python -m vyn.cli run examples/match_demo.vyn
python -m vyn.cli run examples/ai_train.vyn
python -m vyn.cli run examples/db_demo.vyn
python -m vynstudio.main

python -m vpm install          # install packages from vyn.toml
python -m vpm add db           # add SQLite package
python -m vpm info ai          # show package API
python -m vpm list
```

## Language features

| Feature | Example |
|---------|---------|
| `hot fn` | Live reload without restart |
| `@[profile]` | Built-in profiling |
| `enum` | `enum Color { Red, Green }` |
| `match/case` | Pattern matching |
| `try/catch/throw` | Error handling |
| `struct/impl` | OOP-style methods |
| `extern "C"` | FFI to C |
| Ownership | `mut`, immutable by default |

## VPM Packages

| Package | Purpose |
|---------|---------|
| `serde` | JSON serialize/deserialize |
| `collections` | Stack, Queue |
| `neural` | ReLU, sigmoid (hot-swap) |
| `ai` | Train & save neural networks |
| `db` | SQLite database |
| `async` | defer_ms, yield |
| `web` | HTML helpers |

## Standard library (31 modules)

Core: `io`, `sys`, `math`, `str`, `fs`, `net`, `http`, `server`, `html`, `css`, `json`, `db`, `ai`, `gui`, `log`

**ML / Data Science (Python bindings):**

| Module | Python | Example |
|--------|--------|---------|
| `std.numpy` | NumPy | `numpy.array([1.0,2.0]); numpy.mean(data)` |
| `std.torch` | PyTorch | `torch.train_linear(50); torch.tensor(data)` |
| `std.tensorflow` | TensorFlow | `tensorflow.train_xor(100)` |
| `std.cv` | OpenCV | `cv.grayscale("in.png","out.png")` |
| `std.pandas` | Pandas | `pandas.read_csv("data.csv")` |
| `std.sklearn` | scikit-learn | `sklearn.fit_linear(xs, ys)` |
| `std.plot` | Matplotlib | `plot.line("chart.png", xs, ys, "title")` |

```bash
pip install numpy pandas scikit-learn matplotlib opencv-python
pip install torch tensorflow   # optional, large
python -m vyn.cli run examples/ml_bindings.vyn
```

## Examples

- `match_demo.vyn` — enum + match + try/catch
- `ai_train.vyn` — neural network training (std.ai + VPM)
- `ml_bindings.vyn` — NumPy, PyTorch, TensorFlow, sklearn, plot
- `ml_cv_pandas.vyn` — OpenCV + Pandas
- `db_demo.vyn` — SQLite database
- `web_server.vyn` — HTTP server
- `gui_app.vyn` — tkinter GUI
- `profile.vyn` — profiling
- `hot_swap.vyn` — hot reload
- `ffi.vyn` — C FFI

## VynStudio IDE

- VS Code Light theme, English UI
- **F5** Run | **Shift+F5** Stop
- Packages & AI panels
- Correct error line numbers
