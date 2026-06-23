"""ML / data-science Python bindings — numpy, torch, tensorflow, cv, pandas, sklearn, plot."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

_TENSORS: Dict[str, Any] = {}
_TID = 0


def _tid() -> str:
    global _TID
    _TID += 1
    return f"t{_TID}"


def _as_list(v: Any) -> list:
    if isinstance(v, list):
        return v
    return [v]


def _import_err(name: str, pip: str) -> str:
    return f"Install {name}: pip install {pip}"


def dispatch_ml(mod: str, method: str, args: list) -> Optional[Any]:
    _MISSING = object()

    # --- numpy ---
    if mod == "numpy":
        try:
            import numpy as np
        except ImportError:
            if method == "version":
                return _import_err("numpy", "numpy")
            return None
        if method == "version":
            return np.__version__
        if method == "array":
            return np.array(_as_list(args[0]), dtype=np.float32).tolist()
        if method == "zeros":
            n = int(args[0]) if args else 0
            return np.zeros(n, dtype=np.float32).tolist()
        if method == "ones":
            n = int(args[0]) if args else 0
            return np.ones(n, dtype=np.float32).tolist()
        if method == "mean":
            return float(np.mean(_as_list(args[0])))
        if method == "dot":
            a, b = _as_list(args[0]), _as_list(args[1])
            return float(np.dot(a, b))
        if method == "shape":
            return len(_as_list(args[0]))
        if method == "reshape":
            arr = np.array(_as_list(args[0]), dtype=np.float32)
            shape = int(args[1]) if len(args) > 1 else len(arr)
            return arr.reshape(shape).tolist()

    # --- pytorch ---
    if mod == "torch":
        try:
            import torch
        except ImportError:
            if method == "version":
                return _import_err("torch", "torch")
            return None
        if method == "version":
            return torch.__version__
        if method == "tensor":
            t = torch.tensor(_as_list(args[0]), dtype=torch.float32)
            hid = _tid()
            _TENSORS[hid] = t
            return hid
        if method == "relu":
            t = _TENSORS.get(str(args[0]))
            if t is None:
                t = torch.tensor(_as_list(args[0]), dtype=torch.float32)
            return torch.relu(t).tolist()
        if method == "train_linear":
            # Mini training loop on y = 2x
            x = torch.tensor([[float(i)] for i in range(10)], dtype=torch.float32)
            y = x * 2.0
            w = torch.randn(1, 1, requires_grad=True)
            b = torch.randn(1, requires_grad=True)
            opt = torch.optim.SGD([w, b], lr=0.01)
            loss_val = 0.0
            for _ in range(int(args[0]) if args else 50):
                pred = x @ w + b
                loss = torch.nn.functional.mse_loss(pred, y)
                opt.zero_grad()
                loss.backward()
                opt.step()
                loss_val = float(loss.item())
            return loss_val
        if method == "save":
            hid = str(args[0])
            path = str(args[1]) if len(args) > 1 else "model.pt"
            t = _TENSORS.get(hid)
            if t is not None:
                torch.save(t, path)
            return 0
        if method == "load":
            path = str(args[0])
            t = torch.load(path, weights_only=True)
            hid = _tid()
            _TENSORS[hid] = t
            return hid

    # --- tensorflow ---
    if mod == "tensorflow":
        try:
            import tensorflow as tf
        except ImportError:
            if method == "version":
                return _import_err("tensorflow", "tensorflow")
            return None
        if method == "version":
            return tf.__version__
        if method == "train_xor":
            epochs = int(args[0]) if args else 100
            x = tf.constant([[0., 0.], [0., 1.], [1., 0.], [1., 1.]], dtype=tf.float32)
            y = tf.constant([[0.], [1.], [1.], [0.]], dtype=tf.float32)
            model = tf.keras.Sequential([
                tf.keras.layers.Dense(4, activation="relu", input_shape=(2,)),
                tf.keras.layers.Dense(1, activation="sigmoid"),
            ])
            model.compile(optimizer="adam", loss="binary_crossentropy")
            hist = model.fit(x, y, epochs=epochs, verbose=0)
            return float(hist.history["loss"][-1])
        if method == "predict":
            # reuse last xor model pattern with inline small net
            x = tf.constant([[float(args[0]), float(args[1]) if len(args) > 1 else 0.0]], dtype=tf.float32)
            net = tf.keras.Sequential([tf.keras.layers.Dense(1, activation="sigmoid", input_shape=(2,))])
            out = net(x)
            return float(out.numpy()[0][0])

    # --- opencv (cv) ---
    if mod == "cv":
        try:
            import cv2
            import numpy as np
        except ImportError:
            if method == "version":
                return _import_err("opencv", "opencv-python")
            return None
        if method == "version":
            return cv2.__version__
        if method == "read_size":
            img = cv2.imread(str(args[0]))
            if img is None:
                return "0x0"
            h, w = img.shape[:2]
            return f"{w}x{h}"
        if method == "grayscale":
            src, dst = str(args[0]), str(args[1])
            img = cv2.imread(src)
            if img is None:
                return 1
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(dst, gray)
            return 0
        if method == "resize":
            src, dst = str(args[0]), str(args[1])
            w, h = int(args[2]), int(args[3]) if len(args) > 3 else int(args[2])
            img = cv2.imread(src)
            if img is None:
                return 1
            out = cv2.resize(img, (w, h))
            cv2.imwrite(dst, out)
            return 0
        if method == "blur":
            src, dst = str(args[0]), str(args[1])
            img = cv2.imread(src)
            if img is None:
                return 1
            out = cv2.GaussianBlur(img, (15, 15), 0)
            cv2.imwrite(dst, out)
            return 0

    # --- pandas ---
    if mod == "pandas":
        try:
            import pandas as pd
        except ImportError:
            if method == "version":
                return _import_err("pandas", "pandas")
            return None
        if method == "version":
            return pd.__version__
        if method == "read_csv":
            df = pd.read_csv(str(args[0]))
            hid = _tid()
            _TENSORS[hid] = df
            return hid
        if method == "rows":
            df = _TENSORS.get(str(args[0]))
            return len(df) if df is not None else 0
        if method == "mean":
            df = _TENSORS.get(str(args[0]))
            col = str(args[1]) if len(args) > 1 else df.columns[0]
            return float(df[col].mean()) if df is not None else 0.0
        if method == "head_json":
            df = _TENSORS.get(str(args[0]))
            n = int(args[1]) if len(args) > 1 else 5
            if df is None:
                return "[]"
            return df.head(n).to_json(orient="records")

    # --- sklearn ---
    if mod == "sklearn":
        try:
            from sklearn.linear_model import LinearRegression
            import numpy as np
        except ImportError:
            if method == "version":
                return _import_err("sklearn", "scikit-learn")
            return None
        if method == "version":
            import sklearn
            return sklearn.__version__
        if method == "fit_linear":
            xs = _as_list(args[0])
            ys = _as_list(args[1])
            X = np.array(xs, dtype=np.float32).reshape(-1, 1)
            y = np.array(ys, dtype=np.float32)
            m = LinearRegression()
            m.fit(X, y)
            hid = _tid()
            _TENSORS[hid] = m
            return hid
        if method == "predict":
            m = _TENSORS.get(str(args[0]))
            x = float(args[1]) if len(args) > 1 else 0.0
            if m is None:
                return 0.0
            import numpy as np
            return float(m.predict(np.array([[x]], dtype=np.float32))[0])
        if method == "score":
            m = _TENSORS.get(str(args[0]))
            xs, ys = _as_list(args[1]), _as_list(args[2])
            if m is None:
                return 0.0
            import numpy as np
            X = np.array(xs, dtype=np.float32).reshape(-1, 1)
            y = np.array(ys, dtype=np.float32)
            return float(m.score(X, y))

    # --- matplotlib (plot) ---
    if mod == "plot":
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            if method == "version":
                return _import_err("matplotlib", "matplotlib")
            return None
        if method == "version":
            return matplotlib.__version__
        if method == "line":
            path = str(args[0])
            xs = _as_list(args[1])
            ys = _as_list(args[2])
            title = str(args[3]) if len(args) > 3 else "Vyn Plot"
            plt.figure(figsize=(8, 4))
            plt.plot(xs, ys, marker="o")
            plt.title(title)
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(path)
            plt.close()
            return 0
        if method == "hist":
            path = str(args[0])
            data = _as_list(args[1])
            plt.figure(figsize=(8, 4))
            plt.hist(data, bins=20, color="#007ACC", edgecolor="white")
            plt.title("Histogram")
            plt.tight_layout()
            plt.savefig(path)
            plt.close()
            return 0

    return None
