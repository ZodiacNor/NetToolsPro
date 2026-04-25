"""
platform_utils — cross-platform abstraction layer for NetTools Pro.

Public API: import the submodules explicitly, e.g.
    from platform_utils import detect, net, shell, scripting, capabilities
"""
from . import detect, net, shell, scripting, capabilities
from .detect import (
    IS_WINDOWS, IS_LINUX, IS_MACOS,
    SUBPROCESS_FLAGS, is_admin, platform_name,
)

__all__ = [
    "detect", "net", "shell", "scripting", "capabilities",
    "IS_WINDOWS", "IS_LINUX", "IS_MACOS",
    "SUBPROCESS_FLAGS", "is_admin", "platform_name",
]
