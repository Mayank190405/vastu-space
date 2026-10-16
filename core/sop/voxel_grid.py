"""
VĀSTU Capture SOP Engine: Real-Time 3D Voxel Coverage Grid
Maintains an on-device spatial occupancy grid tracking camera view frustum observations.
Enforces the 85% gated completion rule to prevent upload of incomplete scans missing floors or walls.
"""

from typing import Dict, Any, List, Tuple, Optional
import math
import numpy as np


class VoxelCoverageGrid:
    """
    3D spatial occupancy grid mapped to the metric room boundary.
    Runs on-device at 30-60 Hz tracking observed floor, wall, and volumetric cells.
    """

    def __init__(
        self,
        width_m: float = 5.0,
        length_m: float = 6.0,
        height_m: float = 2.8,
        grid_dim: int = 10
    ):
        self.width_m = max(1.0, width_m)
        self.length_m = max(1.0, length_m)
        self.height_m = max(1.0, height_m)
        self.grid_dim = grid_dim

        # Voxel step sizes
        self.dx = self.width_m / float(grid_dim)
        self.dy = self.length_m / float(grid_dim)
        self.dz = self.height_m / float(grid_dim)

        # 3D occupancy grid (0 = unobserved, 1 = observed)
        self.grid_3d = np.zeros((grid_dim, grid_dim, grid_dim), dtype=np.uint8)

        # 2D surface occupancy grids
        self.floor_grid = np.zeros((grid_dim, grid_dim), dtype=np.uint8)
        self.ceiling_grid = np.zeros((grid_dim, grid_dim), dtype=np.uint8)

        # 4 walls: North (y=0), South (y=length), West (x=0), East (x=width)
        self.wall_north = np.zeros((grid_dim, grid_dim), dtype=np.uint8)  # (x, z)
        self.wall_south = np.zeros((grid_dim, grid_dim), dtype=np.uint8)  # (x, z)
        self.wall_west = np.zeros((grid_dim, grid_dim), dtype=np.uint8)   # (y, z)
        self.wall_east = np.zeros((grid_dim, grid_dim), dtype=np.uint8)   # (y, z)

        self.total_observations = 0
        self.last_position: Optional[Tuple[float, float, float]] = None

    def _world_to_grid(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        gx = int(np.clip(x / self.dx, 0, self.grid_dim - 1))
        gy = int(np.clip(y / self.dy, 0, self.grid_dim - 1))
        gz = int(np.clip(z / self.dz, 0, self.grid_dim - 1))
        return gx, gy, gz

    def update_pose(
        self,
        position: Tuple[float, float, float],
        look_direction: Tuple[float, float, float],
        fov_deg: float = 65.0,
        max_range_m: float = 4.5
    ):
        """
        Updates grid cells and surface planes observed by the camera frustum.
        position: (x, y, z) in meters (z is up)
        look_direction: (dx, dy, dz) normalized viewing vector
        """
        self.total_observations += 1
        px, py, pz = position
        self.last_position = (px, py, pz)

        # Normalize look direction
        norm = math.sqrt(look_direction[0]**2 + look_direction[1]**2 + look_direction[2]**2)
        if norm < 1e-6:
            ld = (0.0, 1.0, 0.0)
        else:
            ld = (look_direction[0] / norm, look_direction[1] / norm, look_direction[2] / norm)

        # Ray-march sample points within frustum cone
        half_fov = math.radians(fov_deg / 2.0)
        num_steps = 15
        step_size = max_range_m / float(num_steps)

        # Sample rays along viewing direction and slight offsets for frustum cone
        ray_offsets = [
            (0.0, 0.0, 0.0),
            (math.sin(half_fov * 0.7), 0.0, 0.0),
            (-math.sin(half_fov * 0.7), 0.0, 0.0),
            (0.0, 0.0, math.sin(half_fov * 0.7)),
            (0.0, 0.0, -math.sin(half_fov * 0.7)),
        ]

        for off_x, off_y, off_z in ray_offsets:
            rx = ld[0] + off_x
            ry = ld[1] + off_y
            rz = ld[2] + off_z
            r_norm = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx / r_norm, ry / r_norm, rz / r_norm

            for step in range(1, num_steps + 1):
                dist = step * step_size
                sx = px + rx * dist
                sy = py + ry * dist
                sz = pz + rz * dist

                # Check if ray hits floor boundary (z <= 0)
                if sz <= 0.05:
                    fgx = int(np.clip(sx / self.dx, 0, self.grid_dim - 1))
                    fgy = int(np.clip(sy / self.dy, 0, self.grid_dim - 1))
                    self.floor_grid[fgx, fgy] = 1

                # Check if ray hits ceiling boundary (z >= height_m)
                if sz >= self.height_m - 0.15:
                    cgx = int(np.clip(sx / self.dx, 0, self.grid_dim - 1))
                    cgy = int(np.clip(sy / self.dy, 0, self.grid_dim - 1))
                    self.ceiling_grid[cgx, cgy] = 1

                # Check if ray hits walls
                if sy <= 0.15:  # North wall
                    wgx = int(np.clip(sx / self.dx, 0, self.grid_dim - 1))
                    wgz = int(np.clip(sz / self.dz, 0, self.grid_dim - 1))
                    self.wall_north[wgx, wgz] = 1
                elif sy >= self.length_m - 0.15:  # South wall
                    wgx = int(np.clip(sx / self.dx, 0, self.grid_dim - 1))
                    wgz = int(np.clip(sz / self.dz, 0, self.grid_dim - 1))
                    self.wall_south[wgx, wgz] = 1

                if sx <= 0.15:  # West wall
                    wgy = int(np.clip(sy / self.dy, 0, self.grid_dim - 1))
                    wgz = int(np.clip(sz / self.dz, 0, self.grid_dim - 1))
                    self.wall_west[wgy, wgz] = 1
                elif sx >= self.width_m - 0.15:  # East wall
                    wgy = int(np.clip(sy / self.dy, 0, self.grid_dim - 1))
                    wgz = int(np.clip(sz / self.dz, 0, self.grid_dim - 1))
                    self.wall_east[wgy, wgz] = 1

                # Update 3D grid cell
                if 0 <= sx < self.width_m and 0 <= sy < self.length_m and 0 <= sz < self.height_m:
                    gx, gy, gz = self._world_to_grid(sx, sy, sz)
                    self.grid_3d[gx, gy, gz] = 1

    @property
    def floor_coverage_fraction(self) -> float:
        total = self.floor_grid.size
        observed = int(np.sum(self.floor_grid))
        return round(float(observed) / float(total), 3)

    @property
    def ceiling_coverage_fraction(self) -> float:
        total = self.ceiling_grid.size
        observed = int(np.sum(self.ceiling_grid))
        return round(float(observed) / float(total), 3)

    @property
    def wall_coverage_fractions(self) -> Dict[str, float]:
        dim_sq = float(self.grid_dim * self.grid_dim)
        return {
            "north": round(float(np.sum(self.wall_north)) / dim_sq, 3),
            "south": round(float(np.sum(self.wall_south)) / dim_sq, 3),
            "west": round(float(np.sum(self.wall_west)) / dim_sq, 3),
            "east": round(float(np.sum(self.wall_east)) / dim_sq, 3)
        }

    @property
    def min_wall_coverage_fraction(self) -> float:
        walls = self.wall_coverage_fractions
        return min(walls.values())

    @property
    def avg_wall_coverage_fraction(self) -> float:
        walls = self.wall_coverage_fractions
        return round(sum(walls.values()) / len(walls), 3)

    @property
    def volume_coverage_fraction(self) -> float:
        total = self.grid_3d.size
        observed = int(np.sum(self.grid_3d))
        return round(float(observed) / float(total), 3)

    @property
    def overall_coverage_fraction(self) -> float:
        """
        Weighted metric score combining floor (35%), walls (45%), and volume/ceiling (20%).
        """
        w_floor = 0.35
        w_walls = 0.45
        w_rest = 0.20
        score = (
            w_floor * self.floor_coverage_fraction +
            w_walls * self.avg_wall_coverage_fraction +
            w_rest * (0.5 * self.ceiling_coverage_fraction + 0.5 * self.volume_coverage_fraction)
        )
        return round(min(1.0, score), 3)

    def is_gated_complete(
        self,
        min_overall: float = 0.85,
        min_floor: float = 0.80,
        min_wall: float = 0.70
    ) -> Tuple[bool, List[str]]:
        """
        Fulfills Acceptance Criterion:
        Blocks capture completion until >= 85% spatial coverage is achieved,
        specifically ensuring floor >= 80% and each wall >= 70% to eliminate foreground holes.
        """
        defects = []
        overall = self.overall_coverage_fraction
        floor = self.floor_coverage_fraction
        walls = self.wall_coverage_fractions

        if overall < min_overall:
            defects.append(
                f"Overall space coverage is {int(overall * 100)}% (required: {int(min_overall * 100)}%)."
            )

        if floor < min_floor:
            defects.append(
                f"Floor coverage is {int(floor * 100)}% (required: {int(min_floor * 100)}%). Tilt phone downward to scan floor and baseboards."
            )

        for wall_name, wall_cov in walls.items():
            if wall_cov < min_wall:
                defects.append(
                    f"{wall_name.capitalize()} wall coverage is {int(wall_cov * 100)}% (required: {int(min_wall * 100)}%). Step toward {wall_name} wall and sweep."
                )

        is_complete = (len(defects) == 0)
        return is_complete, defects

    def get_summary(self) -> Dict[str, Any]:
        is_complete, defects = self.is_gated_complete()
        return {
            "overall_coverage_pct": int(self.overall_coverage_fraction * 100),
            "floor_coverage_pct": int(self.floor_coverage_fraction * 100),
            "ceiling_coverage_pct": int(self.ceiling_coverage_fraction * 100),
            "wall_coverage_pcts": {k: int(v * 100) for k, v in self.wall_coverage_fractions.items()},
            "is_gated_complete": is_complete,
            "completion_defects": defects,
            "total_observations": self.total_observations
        }
