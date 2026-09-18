"""
VĀSTU Indoor Navigation Engine: Turn-by-Turn Instruction Generator
Transforms 3D waypoints into human-readable turn directions.
"""

from typing import List, Dict, Any
import numpy as np

def generate_turn_instructions(waypoints: List[List[float]]) -> List[Dict[str, Any]]:
    """
    Generates step-by-step turn instructions (Straight, Turn Left, Turn Right, Arrive) from waypoints.
    """
    if len(waypoints) < 2:
        return [{"step": 1, "instruction": "You are at your destination", "type": "arrive"}]

    steps = []
    pts = [np.array(w) for w in waypoints]

    for i in range(len(pts) - 1):
        dist = float(np.linalg.norm(pts[i + 1] - pts[i]))
        if i == 0:
            turn_type = "straight"
            text = f"Proceed straight for {dist:.1f} meters"
        elif i == len(pts) - 2:
            turn_type = "arrive"
            text = f"Walk {dist:.1f} meters to your destination"
        else:
            # Angle check between vectors
            v1 = pts[i] - pts[i - 1]
            v2 = pts[i + 1] - pts[i]
            cross_z = v1[0] * v2[2] - v1[2] * v2[0]  # Horizontal plane 2D cross product

            if abs(cross_z) < 0.1:
                turn_type = "straight"
                text = f"Continue straight for {dist:.1f} meters"
            elif cross_z > 0:
                turn_type = "turn_right"
                text = f"Turn right and walk for {dist:.1f} meters"
            else:
                turn_type = "turn_left"
                text = f"Turn left and walk for {dist:.1f} meters"

        steps.append({
            "step": i + 1,
            "instruction": text,
            "turn_type": turn_type,
            "distance_m": round(dist, 2),
            "from_point": pts[i].tolist(),
            "to_point": pts[i + 1].tolist()
        })

    return steps
