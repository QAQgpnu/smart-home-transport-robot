from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot


Point = tuple[float, float]
Cell = tuple[int, int]


@dataclass(frozen=True)
class GridMap:
    width: int
    height: int
    blocked: frozenset[Cell]
    resolution: float = 1.0

    def in_bounds(self, cell: Cell) -> bool:
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def is_free(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and cell not in self.blocked

    def center(self, cell: Cell) -> Point:
        return ((cell[0] + 0.5) * self.resolution, (cell[1] + 0.5) * self.resolution)


@dataclass
class RobotState:
    x: float
    y: float
    yaw: float
    v: float = 0.0
    w: float = 0.0

    @property
    def point(self) -> Point:
        return (self.x, self.y)


@dataclass(frozen=True)
class DynamicObstacle:
    x: float
    y: float
    radius: float
    appears_at_step: int


@dataclass(frozen=True)
class Scenario:
    grid: GridMap
    start: Cell
    goal: Cell
    dynamic_obstacles: tuple[DynamicObstacle, ...] = field(default_factory=tuple)


def distance(a: Point, b: Point) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def default_scenario() -> Scenario:
    width, height = 24, 16
    blocked: set[Cell] = set()

    # Outer wall with openings at the start and goal side.
    for x in range(width):
        blocked.add((x, 0))
        blocked.add((x, height - 1))
    for y in range(height):
        blocked.add((0, y))
        blocked.add((width - 1, y))

    # Furniture islands form a small apartment-like navigation scene.
    for x in range(5, 10):
        for y in range(3, 6):
            blocked.add((x, y))
    for x in range(4, 8):
        for y in range(10, 13):
            blocked.add((x, y))
    for x in range(13, 18):
        for y in range(5, 8):
            blocked.add((x, y))
    for x in range(15, 21):
        for y in range(11, 13):
            blocked.add((x, y))
    for y in range(2, 11):
        blocked.add((11, y))
    blocked.remove((11, 8))
    blocked.remove((11, 9))

    return Scenario(
        grid=GridMap(width, height, frozenset(blocked)),
        start=(2, 13),
        goal=(21, 2),
        dynamic_obstacles=(DynamicObstacle(12.4, 9.1, 0.65, 36),),
    )
