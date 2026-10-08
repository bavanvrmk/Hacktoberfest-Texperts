"""
tests/test_member2_phase4_edge_cases.py
Member 2 - Phase 4: Edge Case Accuracy Testing across Multiple Desktop Apps
==========================================================================
Verifies that mouse clicks land accurately inside extremely disproportionate,
small, or edge-touching bounding boxes found in apps like Excel, Web Browsers,
and PDF Readers. Ensures no target coords fall out of bounds.
"""

import unittest
from core.mouse_executor import (
    sample_human_target_point,
    normalize_bounding_box,
    get_screen_resolution,
    execute_action_loop
)

class TestDesktopAppEdgeCases(unittest.TestCase):
    
    def setUp(self):
        self.screen_w, self.screen_h = get_screen_resolution()
        
    def _verify_point_in_box(self, point, bbox):
        px, py = point
        x1, y1, x2, y2 = bbox
        
        # Ensure x is safely inside
        self.assertGreaterEqual(px, x1)
        self.assertLessEqual(px, x2)
        
        # Ensure y is safely inside
        self.assertGreaterEqual(py, y1)
        self.assertLessEqual(py, y2)

    def test_excel_wide_ribbon_button(self):
        """
        Excel Ribbon buttons can be extremely wide but very short.
        Verify Gaussian sampler doesn't overshoot Y-axis.
        """
        bbox = (100, 50, 1000, 70) # 900px wide, 20px high
        for _ in range(50):
            pt = sample_human_target_point(bbox)
            self._verify_point_in_box(pt, bbox)
            
    def test_excel_tiny_cell(self):
        """
        Excel cells can be very tiny (e.g., 20x15).
        Verify we still land accurately inside without failsafe triggering.
        """
        bbox = (300, 300, 320, 315)
        for _ in range(50):
            pt = sample_human_target_point(bbox)
            self._verify_point_in_box(pt, bbox)

    def test_browser_tiny_close_button(self):
        """
        Browser tab 'X' buttons are extremely small and near the screen top.
        """
        bbox = (self.screen_w - 50, 0, self.screen_w - 30, 20)
        for _ in range(50):
            pt = sample_human_target_point(bbox)
            self._verify_point_in_box(pt, bbox)

    def test_browser_url_bar(self):
        """
        URL address bar is extremely wide. Click must remain safely inside.
        """
        bbox = (150, 40, self.screen_w - 100, 75)
        for _ in range(50):
            pt = sample_human_target_point(bbox)
            self._verify_point_in_box(pt, bbox)

    def test_pdf_reader_corner_scrolling(self):
        """
        Scrollbar arrows at the very right/bottom edge of the screen.
        Verify clamping logic keeps coordinates strictly inside display limits.
        """
        bbox = (self.screen_w - 15, self.screen_h - 15, self.screen_w, self.screen_h)
        for _ in range(50):
            pt = sample_human_target_point(bbox)
            self._verify_point_in_box(pt, bbox)
            
            # Additional clamp check
            self.assertLess(pt[0], self.screen_w)
            self.assertLess(pt[1], self.screen_h)

    def test_out_of_bounds_recovery(self):
        """
        If Vision model returns coordinates slightly outside the screen,
        normalize_bounding_box should clamp them properly.
        """
        # Imagine a bbox that overflows the screen boundaries
        overflow_bbox = [self.screen_w - 20, -50, self.screen_w + 50, 100]
        clamped_bbox = normalize_bounding_box(overflow_bbox)
        
        self.assertEqual(clamped_bbox[0], self.screen_w - 20)
        self.assertEqual(clamped_bbox[1], 0)
        self.assertEqual(clamped_bbox[2], self.screen_w - 1)
        self.assertEqual(clamped_bbox[3], 100)

    def test_full_edge_case_dry_run_pipeline(self):
        """
        Test the entire execution loop with difficult boundaries.
        """
        payload = {
            "steps": [
                {"action": "click", "bbox": [0, 0, 15, 15], "text": "Top left browser menu"},
                {"action": "double_click", "bbox": [0.98, 0.98, 1.0, 1.0], "text": "Bottom right corner"},
                {"action": "scroll", "amount": 5}
            ]
        }
        res = execute_action_loop(payload, dry_run=True)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["executed_steps"], 3)
        self.assertEqual(res["failed_steps"], 0)

if __name__ == "__main__":
    unittest.main()
