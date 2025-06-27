from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class LineCode:
    source: int
    destination: int
    line: str

@dataclass
class Segment:
    type: str
    lines: List[LineCode] = field(default_factory=list)

@dataclass
class FileObject:
    toString: str

@dataclass
class Hunk:
    segments: List[Segment] = field(default_factory=list)

@dataclass
class Diff:
    destination: Optional[FileObject]
    hunks: List[Hunk] = field(default_factory=list)

@dataclass
class DiffResponse:
    diffs: List[Diff] = field(default_factory=list) 