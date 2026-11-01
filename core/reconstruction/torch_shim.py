"""
Lightweight Pure-Python / NumPy PyTorch Compatibility Shim.
Enables execution of VĀSTU pipelines when full PyTorch binary is unavailable.
"""

import numpy as np


def set_num_threads(n: int):
    pass


class Device:
    def __init__(self, type_str: str = "cpu"):
        self.type = type_str

    def __str__(self):
        return self.type

    def __repr__(self):
        return f"device(type='{self.type}')"


def device(d="cpu"):
    return Device(str(d))


class Cuda:
    @staticmethod
    def is_available() -> bool:
        return False


cuda = Cuda()


class no_grad:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Tensor(np.ndarray):
    def __new__(cls, input_array):
        obj = np.asarray(input_array).view(cls)
        return obj

    def to(self, device):
        return self

    def permute(self, *dims):
        return Tensor(np.transpose(self, dims))

    def unsqueeze(self, axis):
        return Tensor(np.expand_dims(self, axis=axis))

    def squeeze(self, axis=None):
        return Tensor(np.squeeze(self, axis=axis))

    def float(self):
        return Tensor(self.astype(np.float32))

    def cpu(self):
        return self

    def numpy(self):
        return np.asarray(self)

    def argmax(self, axis=None):
        return Tensor(np.argmax(self, axis=axis))

    def view(self, *shape):
        return Tensor(self.reshape(*shape))


def from_numpy(arr: np.ndarray) -> Tensor:
    return Tensor(arr)


def tensor(data, dtype=None) -> Tensor:
    return Tensor(np.array(data, dtype=dtype))

