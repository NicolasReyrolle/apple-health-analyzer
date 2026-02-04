"""Protocol for UI state assertion functions."""
from typing import Protocol, Optional, Any
from nicegui.testing import UserInteraction

class StateAssertion(Protocol):
    """Protocol for UI state assertion functions."""
    def __call__(
        self,
        interaction: UserInteraction[Any],
        enabled: Optional[bool] = None,
        visible: Optional[bool] = None,
    ) -> None: ...
