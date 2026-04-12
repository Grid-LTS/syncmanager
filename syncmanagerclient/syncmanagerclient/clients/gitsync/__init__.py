from pathlib import PurePosixPath, Path
import uuid
from typing import Tuple

from .. import get_remote_url


def sanitize_remote_url(url: str) -> Tuple[str, str]:
    url_path = Path(url)
    segments = url_path.parts
    crucial_start_index = segments.index("git") + 1
    crucial_segments = segments[crucial_start_index:]
    url_prefix = get_remote_url(url.replace("/" + str(PurePosixPath(*crucial_segments)), ""))
    # safety checks that we collect the right positions
    try:
        uuid.UUID(crucial_segments[1])
        crucial_segments = crucial_segments[1:]
    except ValueError:
        pass
    if crucial_segments[-2].endswith(".git"):
        crucial_segments = crucial_segments[:-1]
    return str(PurePosixPath(*crucial_segments)), url_prefix
