"""Semilla global para que una corrida se pueda repetir."""

import os
import random


def set_global_seed(seed: int) -> None:
    """Fija random, numpy y torch si están instalados.

    Los entornos de Gymnasium se siembran aparte, con env.reset(seed=...).
    PYTHONHASHSEED solo afecta a los subprocesos que se lancen después.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    try:
        import numpy as np
    except ImportError:
        pass
    else:
        np.random.seed(seed)
    try:
        import torch
    except ImportError:
        pass
    else:
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
