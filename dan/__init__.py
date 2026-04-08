"""
DAN — Deep Agent Network Framework
A generalized end-to-end learning framework without gradients.

Users only need to provide: META, HEURISTIC, PARAM, LOSS as task definitions.
The framework handles the rest automatically.
"""

from dan.core import META, HEURISTIC, PARAM, LOSS
from dan.runner import Runner
from dan.utils import print_header, print_step

__version__ = "0.1.0"
__all__ = ["META", "HEURISTIC", "PARAM", "LOSS", "Runner"]
