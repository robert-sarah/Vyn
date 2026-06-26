"""Vyn AI runtime — lightweight neural network training."""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class VynModel:
    name: str
    input_size: int
    hidden_size: int
    output_size: int
    weights_ih: List[List[float]] = field(default_factory=list)
    weights_ho: List[List[float]] = field(default_factory=list)
    bias_h: List[float] = field(default_factory=list)
    bias_o: List[float] = field(default_factory=list)
    epochs_done: int = 0
    last_loss: float = 0.0

    def __post_init__(self):
        if not self.weights_ih:
            self._init_weights()

    def _init_weights(self) -> None:
        self.weights_ih = [
            [random.uniform(-0.5, 0.5) for _ in range(self.input_size)]
            for _ in range(self.hidden_size)
        ]
        self.weights_ho = [
            [random.uniform(-0.5, 0.5) for _ in range(self.hidden_size)]
            for _ in range(self.output_size)
        ]
        self.bias_h = [0.0] * self.hidden_size
        self.bias_o = [0.0] * self.output_size


_models: Dict[str, VynModel] = {}
_counter = 0


def _next_id() -> str:
    global _counter
    _counter += 1
    return f"model_{_counter}"


def _relu(x: float) -> float:
    return x if x > 0 else 0.0


def _relu_deriv(x: float) -> float:
    return 1.0 if x > 0 else 0.0


def _sigmoid(x: float) -> float:
    x = max(-20.0, min(20.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def _softmax(vals: List[float]) -> List[float]:
    m = max(vals)
    ex = [math.exp(v - m) for v in vals]
    s = sum(ex) or 1.0
    return [v / s for v in ex]


def model_create(name: str, inputs: int, hidden: int, outputs: int) -> str:
    mid = _next_id()
    _models[mid] = VynModel(name or mid, int(inputs), int(hidden), int(outputs))
    return mid


def model_train(model_id: str, epochs: int, lr: float) -> float:
    m = _models.get(str(model_id))
    if not m:
        return -1.0
    lr = float(lr)
    # XOR-like synthetic dataset for demo training
    data = [
        ([0.0, 0.0], [0.0]),
        ([0.0, 1.0], [1.0]),
        ([1.0, 0.0], [1.0]),
        ([1.0, 1.0], [0.0]),
    ]
    total_loss = 0.0
    n = max(1, int(epochs))
    for _ in range(n):
        epoch_loss = 0.0
        for xin, ytarget in data:
            # pad/truncate input
            x = list(xin) + [0.0] * m.input_size
            x = x[: m.input_size]
            # forward
            hidden = []
            for j in range(m.hidden_size):
                s = m.bias_h[j] + sum(m.weights_ih[j][i] * x[i] for i in range(m.input_size))
                hidden.append(_relu(s))
            out_raw = []
            for k in range(m.output_size):
                s = m.bias_o[k] + sum(m.weights_ho[k][j] * hidden[j] for j in range(m.hidden_size))
                out_raw.append(s)
            out = _softmax(out_raw) if m.output_size > 1 else [_sigmoid(out_raw[0])]
            target = ytarget + [0.0] * m.output_size
            target = target[: m.output_size]
            # MSE loss (borné pour éviter overflow)
            loss = sum(min(1e6, (out[i] - target[i]) ** 2) for i in range(m.output_size))
            epoch_loss += loss
            # backward (simplified)
            for k in range(m.output_size):
                grad = 2 * (out[k] - target[k])
                for j in range(m.hidden_size):
                    m.weights_ho[k][j] -= lr * grad * hidden[j]
                m.bias_o[k] -= lr * grad
            for j in range(m.hidden_size):
                gh = sum(
                    2 * (out[k] - target[k]) * m.weights_ho[k][j]
                    for k in range(m.output_size)
                ) * _relu_deriv(hidden[j])
                for i in range(m.input_size):
                    m.weights_ih[j][i] -= lr * gh * x[i]
                m.bias_h[j] -= lr * gh
        total_loss = epoch_loss / len(data)
    m.epochs_done += n
    m.last_loss = total_loss
    return total_loss


def model_predict(model_id: str, x: float) -> float:
    m = _models.get(str(model_id))
    if not m:
        return 0.0
    xv = [float(x)] + [0.0] * (m.input_size - 1)
    xv = xv[: m.input_size]
    hidden = []
    for j in range(m.hidden_size):
        s = m.bias_h[j] + sum(m.weights_ih[j][i] * xv[i] for i in range(m.input_size))
        hidden.append(_relu(s))
    out_raw = []
    for k in range(m.output_size):
        s = m.bias_o[k] + sum(m.weights_ho[k][j] * hidden[j] for j in range(m.hidden_size))
        out_raw.append(s)
    out = _softmax(out_raw) if m.output_size > 1 else [_sigmoid(out_raw[0])]
    return float(out[0])


def model_loss(model_id: str) -> float:
    m = _models.get(str(model_id))
    return m.last_loss if m else 0.0


def model_epochs(model_id: str) -> int:
    m = _models.get(str(model_id))
    return m.epochs_done if m else 0


def model_save(model_id: str, path: str) -> int:
    m = _models.get(str(model_id))
    if not m:
        return 1
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "name": m.name,
        "input_size": m.input_size,
        "hidden_size": m.hidden_size,
        "output_size": m.output_size,
        "weights_ih": m.weights_ih,
        "weights_ho": m.weights_ho,
        "bias_h": m.bias_h,
        "bias_o": m.bias_o,
        "epochs_done": m.epochs_done,
        "last_loss": m.last_loss,
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    return 0


def model_load(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    data = json.loads(p.read_text(encoding="utf-8"))
    mid = _next_id()
    m = VynModel(
        data["name"], data["input_size"], data["hidden_size"], data["output_size"],
        data["weights_ih"], data["weights_ho"], data["bias_h"], data["bias_o"],
        data.get("epochs_done", 0), data.get("last_loss", 0.0),
    )
    _models[mid] = m
    return mid


def dispatch_ai(method: str, args: list) -> Any:
    if method == "model_new":
        return model_create(str(args[0]) if args else "net", int(args[1]) if len(args) > 1 else 2,
                           int(args[2]) if len(args) > 2 else 4, int(args[3]) if len(args) > 3 else 1)
    if method == "train":
        return model_train(str(args[0]), int(args[1]) if len(args) > 1 else 100,
                           float(args[2]) if len(args) > 2 else 0.1)
    if method == "predict":
        return model_predict(str(args[0]), float(args[1]) if len(args) > 1 else 0.0)
    if method == "loss":
        return model_loss(str(args[0]))
    if method == "epochs":
        return model_epochs(str(args[0]))
    if method == "save":
        return model_save(str(args[0]), str(args[1]) if len(args) > 1 else "model.json")
    if method == "load":
        return model_load(str(args[0]))
    return None
