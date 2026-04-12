from pathlib import PurePosixPath
import uuid
from typing import Tuple


def sanitize_remote_url(url) -> Tuple[str,str]:
    segments = url.split("/")
    crucial_start_index = segments.index("git") + 1
    crucial_segments = segments[crucial_start_index:]
    # safety checks that we collect the right positions
    try:
        uuid.UUID(crucial_segments[1])
        crucial_segments = crucial_segments[1:]
    except ValueError:
        pass
    if crucial_segments[-2].endswith(".git"):
        crucial_segments=crucial_segments[:-1]
    return str(PurePosixPath(*crucial_segments)), "/".join(segments[:crucial_start_index])
