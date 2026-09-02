from __future__ import annotations

import heapq
import math
from dataclasses import asdict

from .model import Cell, GridMap, Point, RobotState, Scenario, distance


NEIGHBORS: tuple[tuple[int, int, float], ...] = (
    (-1, 0, 1.0),
    (1, 0, 1.0),
    (0, -1, 1.0),
    (0, 1, 1.0),
    (-1, -1, math.sqrt(2.0)),
    (-1, 1, math.sqrt(2.0)),
    (1, -1, math.sqrt(2.0)),
    (1, 1, math.sqrt(2.0)),
)


def dijkstra(grid: GridMap, start: Cell, goal: Cell) -> list[Cell]:
    """Return a shortest collision-free grid path using 8-connected Dijkstra."""
    if not grid.is_free(start) or not grid.is_free(goal):
        raise ValueError("start and goal must be free cells")

    queue: list[tuple[float, Cell]] = [(0.0, start)]
    cost: dict[Cell, float] = {start: 0.0}
    previous: dict[Cell, Cell] = {}

    while queue:
        current_cost, current = heapq.heappop(queue)
        if current == goal:
            break
        if current_cost != cost[current]:
            continue

        for dx, dy, move_cost in NEIGHBORS:
            nxt = (current[0] + dx, current[1] + dy)
            if not grid.is_free(nxt):
                continue
            if dx and dy:
                # Prevent diagonal corner cutting.
                if not grid.is_free((current[0] + dx, current[1])):
                    continue
                if not grid.is_free((current[0], current[1] + dy)):
                    continue
            candidate = current_cost + move_cost
            if candidate < cost.get(nxt, math.inf):
                cost[nxt] = candidate
                previous[nxt] = current
                heapq.heappush(queue, (candidate, nxt))

    if goal not in cost:
        raise ValueError("goal is unreachable")

    path = [goal]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()
    return path


def _wrap(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def _static_points(grid: GridMap) -> list[Point]:
    return [grid.center(cell) for cell in grid.blocked]


def _clearance(point: Point, obstacles: list[tuple[float, float, float]]) -> float:
    return min((distance(point, (x, y)) - radius for x, y, radius in obstacles), default=99.0)


def _nearest_path_distance(point: Point, path: list[Point]) -> float:
    return min(distance(point, waypoint) for waypoint in path)


def _rollout(state: RobotState, v: float, w: float, horizon: float, dt: float) -> list[RobotState]:
    trial = RobotState(state.x, state.y, state.yaw, v, w)
    trajectory: list[RobotState] = []
    for _ in range(round(horizon / dt)):
        trial.x += v * math.cos(trial.yaw) * dt
        trial.y += v * math.sin(trial.yaw) * dt
        trial.yaw = _wrap(trial.yaw + w * dt)
        trajectory.append(RobotState(trial.x, trial.y, trial.yaw, v, w))
    return trajectory


def _lookahead(state: RobotState, path: list[Point], distance_ahead: float = 2.3) -> Point:
    nearest = min(range(len(path)), key=lambda i: distance(state.point, path[i]))
    target = path[nearest]
    travelled = 0.0
    for i in range(nearest + 1, len(path)):
        travelled += distance(path[i - 1], path[i])
        target = path[i]
        if travelled >= distance_ahead:
            break
    return target


def _dwa_command(
    state: RobotState,
    path: list[Point],
    target: Point,
    obstacles: list[tuple[float, float, float]],
) -> tuple[float, float, list[RobotState]]:
    dt = 0.2
    max_speed, max_yaw_rate = 1.15, 1.45
    max_accel, max_yaw_accel = 0.75, 2.2
    robot_radius = 0.34

    v_min = max(0.0, state.v - max_accel * dt)
    v_max = min(max_speed, state.v + max_accel * dt)
    w_min = max(-max_yaw_rate, state.w - max_yaw_accel * dt)
    w_max = min(max_yaw_rate, state.w + max_yaw_accel * dt)

    best: tuple[float, float, float, list[RobotState]] | None = None
    for vi in range(7):
        v = v_min + (v_max - v_min) * vi / 6.0
        for wi in range(13):
            w = w_min + (w_max - w_min) * wi / 12.0
            rollout = _rollout(state, v, w, horizon=1.4, dt=dt)
            min_clearance = min(_clearance(s.point, obstacles) for s in rollout)
            if min_clearance <= robot_radius:
                continue
            end = rollout[-1]
            desired_yaw = math.atan2(target[1] - end.y, target[0] - end.x)
            score = (
                2.2 * distance(end.point, target)
                + 1.0 * _nearest_path_distance(end.point, path)
                + 0.55 * abs(_wrap(desired_yaw - end.yaw))
                + 0.75 / max(min_clearance, 0.08)
                + 0.35 * (max_speed - v)
            )
            candidate = (score, v, w, rollout)
            if best is None or candidate[0] < best[0]:
                best = candidate

    if best is None:
        return 0.0, 0.8, _rollout(state, 0.0, 0.8, horizon=1.4, dt=dt)
    return best[1], best[2], best[3]


def simulate_navigation(scenario: Scenario, max_steps: int = 520) -> dict:
    cells = dijkstra(scenario.grid, scenario.start, scenario.goal)
    path = [scenario.grid.center(cell) for cell in cells]
    start = path[0]
    next_point = path[1]
    state = RobotState(start[0], start[1], math.atan2(next_point[1] - start[1], next_point[0] - start[0]))
    goal = path[-1]
    static = [(x, y, 0.51) for x, y in _static_points(scenario.grid)]
    states = [RobotState(**asdict(state))]
    candidate_snapshots: list[dict] = []
    min_clearance = math.inf
    dynamic_triggered = False

    for step in range(max_steps):
        if distance(state.point, goal) <= 0.55:
            break
        dynamic = [
            (o.x, o.y, o.radius)
            for o in scenario.dynamic_obstacles
            if step >= o.appears_at_step
        ]
        dynamic_triggered = dynamic_triggered or bool(dynamic)
        obstacles = static + dynamic
        target = _lookahead(state, path)
        v, w, rollout = _dwa_command(state, path, target, obstacles)
        if step % 8 == 0:
            candidate_snapshots.append(
                {
                    "step": step,
                    "target": [round(target[0], 3), round(target[1], 3)],
                    "preview": [[round(s.x, 3), round(s.y, 3)] for s in rollout],
                }
            )
        state.x += v * math.cos(state.yaw) * 0.2
        state.y += v * math.sin(state.yaw) * 0.2
        state.yaw = _wrap(state.yaw + w * 0.2)
        state.v, state.w = v, w
        min_clearance = min(min_clearance, _clearance(state.point, obstacles))
        states.append(RobotState(**asdict(state)))
    else:
        raise RuntimeError("navigation did not converge within max_steps")

    route_length = sum(distance(states[i - 1].point, states[i].point) for i in range(1, len(states)))
    return {
        "scenario": {
            "width": scenario.grid.width,
            "height": scenario.grid.height,
            "blocked": [list(cell) for cell in sorted(scenario.grid.blocked)],
            "start": list(scenario.start),
            "goal": list(scenario.goal),
            "dynamic_obstacles": [asdict(o) for o in scenario.dynamic_obstacles],
        },
        "global_path": [[round(x, 3), round(y, 3)] for x, y in path],
        "trajectory": [
            {
                "x": round(s.x, 3),
                "y": round(s.y, 3),
                "yaw": round(s.yaw, 4),
                "v": round(s.v, 3),
                "w": round(s.w, 3),
            }
            for s in states
        ],
        "candidate_snapshots": candidate_snapshots,
        "metrics": {
            "reached_goal": distance(states[-1].point, goal) <= 0.55,
            "steps": len(states) - 1,
            "simulated_seconds": round((len(states) - 1) * 0.2, 1),
            "route_length": round(route_length, 2),
            "minimum_clearance": round(min_clearance, 2),
            "dynamic_obstacle_triggered": dynamic_triggered,
            "final_goal_error": round(distance(states[-1].point, goal), 3),
        },
    }
