"""
tests/test_mouse_executor.py
Unit and integration tests for Member 2 (OS Sandbox Lead) Phase 2 deliverables:
- Bézier trajectory kinematics and bounds
- Bounding box coordinate normalizer
- Truncated Gaussian target sampling
- Application window focus manager
- Multi-step action loop execution
"""

import unittest
import math
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.mouse_executor import (
    HumanTrajectoryGenerator,
    WindowFocusManager,
    normalize_bounding_box,
    sample_human_target_point,
    ActionExecutor,
    execute_action_loop,
    get_screen_resolution
)

class TestMouseExecutor(unittest.TestCase):

    def setUp(self):
        self.screen_w, self.screen_h = get_screen_resolution()

    def test_trajectory_generation(self):
        """Test Bézier path generation preserves start, end, and screen bounds."""
        start = (100, 100)
        target = (500, 400)
        path = HumanTrajectoryGenerator.generate_trajectory(start, target, min_steps=20, max_steps=40)
        
        self.assertGreaterEqual(len(path), 20)
        self.assertEqual(path[-1], target)
        
        # Verify all coordinates are within screen bounds
        for px, py in path:
            self.assertGreaterEqual(px, 0)
            self.assertLess(px, self.screen_w)
            self.assertGreaterEqual(py, 0)
            self.assertLess(py, self.screen_h)

    def test_trajectory_short_distance(self):
        """Test that sub-threshold movements return immediately to target."""
        start = (100, 100)
        target = (101, 102)
        path = HumanTrajectoryGenerator.generate_trajectory(start, target)
        self.assertEqual(path, [target])

    def test_coordinate_normalization_normalized_inputs(self):
        """Test conversion of Member 1's 0.0-1.0 bounding box to screen pixels."""
        norm_bbox = [0.1, 0.2, 0.3, 0.4]
        left, top, right, bottom = normalize_bounding_box(norm_bbox)
        
        expected_left = int(round(0.1 * self.screen_w))
        expected_top = int(round(0.2 * self.screen_h))
        expected_right = int(round(0.3 * self.screen_w))
        expected_bottom = int(round(0.4 * self.screen_h))
        
        self.assertEqual((left, top, right, bottom), (expected_left, expected_top, expected_right, expected_bottom))

    def test_coordinate_normalization_absolute_inputs(self):
        """Test handling of pre-scaled absolute pixel bounding boxes."""
        abs_bbox = [150, 200, 350, 400]
        left, top, right, bottom = normalize_bounding_box(abs_bbox)
        self.assertEqual((left, top, right, bottom), (150, 200, 350, 400))

    def test_gaussian_sampling_within_bounds(self):
        """Test that sampled click points always land inside the bounding box."""
        bbox = (200, 200, 400, 400)
        for _ in range(50):
            tx, ty = sample_human_target_point(bbox)
            self.assertGreaterEqual(tx, 200)
            self.assertLessEqual(tx, 400)
            self.assertGreaterEqual(ty, 200)
            self.assertLessEqual(ty, 400)

    def test_action_loop_dry_run(self):
        """Test comprehensive action loop processing in dry-run mode."""
        payload = {
            "steps": [
                {"action": "click", "bbox": [0.2, 0.2, 0.4, 0.3]},
                {"action": "type", "text": "Test automation string"},
                {"action": "double_click", "bbox": [500, 500, 550, 530]},
                {"action": "hotkey", "keys": ["ctrl", "c"]},
                {"action": "scroll", "amount": -2}
            ]
        }
        res = execute_action_loop(payload, dry_run=True)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["executed_steps"], 5)
        self.assertEqual(res["failed_steps"], 0)

    def test_single_grounding_model_output(self):
        """Test handling direct single bounding box output from VisionGrounder."""
        vision_output = {
            "target_found": True,
            "confidence": 0.98,
            "bounding_box": [0.25, 0.35, 0.45, 0.55],
            "action": "click"
        }
        res = execute_action_loop(vision_output, dry_run=True)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["executed_steps"], 1)

    def test_self_healing_retry_loop(self):
        """Test SelfHealingExecutor triggers retry when UI does not change."""
        from core.self_healing import SelfHealingExecutor, UIStateValidator
        
        callback_count = [0]
        def mock_reground(desc):
            callback_count[0] += 1
            return {"target_found": True, "bounding_box": [0.4, 0.4, 0.6, 0.6]}

        sh = SelfHealingExecutor(grounder_callback=mock_reground, dry_run=True)
        res = sh.execute_with_self_healing(
            target_description="Submit Form",
            initial_bbox=[0.1, 0.1, 0.2, 0.2]
        )
        self.assertEqual(res["status"], "success")

    def test_ui_state_validator_delta(self):
        """Test UIStateValidator computes correct delta for identical and varied arrays."""
        from core.self_healing import UIStateValidator
        import numpy as np

        img_a = np.zeros((50, 50, 3), dtype=np.uint8)
        img_b = np.zeros((50, 50, 3), dtype=np.uint8)
        delta_zero = UIStateValidator.compute_visual_difference(img_a, img_b)
        self.assertEqual(delta_zero, 0.0)

        img_c = np.ones((50, 50, 3), dtype=np.uint8) * 255
        delta_max = UIStateValidator.compute_visual_difference(img_a, img_c)
        self.assertAlmostEqual(delta_max, 1.0, places=4)

if __name__ == "__main__":
    unittest.main()

