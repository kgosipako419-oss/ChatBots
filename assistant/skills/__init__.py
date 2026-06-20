"""Skills register tools on import. Import this package to load all skills."""
from . import pc_control       # noqa: F401
from . import system_control   # noqa: F401
from . import files            # noqa: F401
from . import reminders        # noqa: F401
from . import notes            # noqa: F401
from . import weather          # noqa: F401
from . import screen           # noqa: F401  accessibility: read screen
from . import ui_control       # noqa: F401  accessibility: click/type by name
from . import dictation        # noqa: F401  speak-to-type
from . import notifications    # noqa: F401
from . import remote           # noqa: F401
