"""pparse constants"""

from typing import Final

# Generally, rerun the parser on same node.
AGAIN: Final[int] = 1
# Generally, run the parser on parent node.
ASCEND: Final[int] = 2

# Generally, rerun the parser on same node (i.e. AGAIN), plus
# pop the state stack if there is more than one state pending.
NEXT: Final[int] = 3
