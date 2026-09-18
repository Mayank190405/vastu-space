"""
Mobile Rescan Guidance & Delta Upload Coordinator:
Simulates step 5, 6, and 7 of the targeted rescan workflow:
5. Send task to mobile
6. Guide user using visual instructions and prioritized TTS
7. Upload only the required additional data for the affected cell
"""

import uuid
from typing import Dict, Any, List, Optional
from core.schemas.rescan_request import RescanRequest

class MobileRescanCoordinator:
    """
    Coordinates mobile retake dispatch, real-time HUD overlays, and delta payload uploads.
    """
    def __init__(self):
        self.active_tasks: Dict[str, RescanRequest] = {}

    def receive_rescan_task(self, task: RescanRequest) -> Dict[str, Any]:
        """
        Step 5: Ingests the rescan task from backend into the mobile capture client.
        """
        self.active_tasks[task.request_id] = task
        task.status = "ASSIGNED"
        return {
            "status": "TASK_RECEIVED",
            "request_id": task.request_id,
            "target_cell": task.cell_id,
            "priority": task.priority,
            "ready_for_guidance": True
        }

    def start_guided_capture(self, request_id: str) -> Dict[str, Any]:
        """
        Step 6: Activates the visual reticle overlay and prioritized audio TTS guidance.
        """
        if request_id not in self.active_tasks:
            raise KeyError(f"Rescan request '{request_id}' not found on mobile device")

        task = self.active_tasks[request_id]
        task.status = "CAPTURING"
        action = task.required_capture_action

        # Build real-time AR HUD overlay configuration
        hud_overlay = {
            "target_box_center_xyz": task.region.center_xyz if task.region else task.target_bounding_box.center_xyz,
            "recommended_distance_m": action.recommended_camera_distance_m if action else 1.5,
            "target_pitch_angle_deg": action.camera_pitch_deg if action else -30.0,
            "guide_pattern": action.capture_pattern if action else "ORBIT_SWEEP",
            "screen_visual_prompt": action.visual_instruction if action else "Perform targeted scan",
            "audio_tts_utterance": action.audio_tts_prompt if action else "Perform targeted scan",
            "haptic_pattern": task.operator_guidance.haptic_cue,
            "waypoints": action.recommended_waypoints if action else []
        }
        return hud_overlay

    def package_delta_upload(
        self,
        request_id: str,
        captured_frames: List[Dict[str, Any]],
        local_imu_samples: List[Dict[str, Any]],
        point_cloud_patch: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Step 7: Uploads ONLY the required additional data for the affected cell.
        Avoids redundant re-upload of full building footage.
        """
        if request_id not in self.active_tasks:
            raise KeyError(f"Rescan request '{request_id}' not found")

        task = self.active_tasks[request_id]
        task.status = "UPLOADED"

        delta_package = {
            "upload_id": f"delta_{task.cell_id}_{uuid.uuid4().hex[:8]}",
            "request_id": task.request_id,
            "project_id": str(task.project_id),
            "target_cell_id": task.cell_id,
            "is_isolated_delta": True,
            "frame_count": len(captured_frames),
            "imu_sample_count": len(local_imu_samples),
            "delta_points_count": len(point_cloud_patch) if point_cloud_patch else 0,
            "delta_data": {
                "frames": captured_frames,
                "imu": local_imu_samples,
                "points": point_cloud_patch or []
            }
        }
        return delta_package
