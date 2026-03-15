"""Typed errors for pipeline diagnostics."""

from __future__ import annotations


class PipelineError(RuntimeError):
    """Base typed pipeline error."""


class PipelineStepError(PipelineError):
    """Failure in a specific pipeline step."""

    def __init__(self, step: str, message: str):
        super().__init__(f"pipeline step '{step}' failed: {message}")
        self.step = step

