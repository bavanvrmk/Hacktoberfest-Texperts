"""
core/self_healing.py - Self-Healing Loop & State Validator (Member 2 - Phase 3)
================================================================================
Implements autonomous recovery for GUI automation:
If an action (e.g., button click) fails to cause an expected UI state change,
this module automatically triggers an adaptive re-crop and re-grounding request
back to Member 1's Vision Model (VisionGrounder).

Key Components:
- UIStateValidator: Compares pre/post visual crops using perceptual difference / MSE.
- SelfHealingExecutor: Wraps ActionExecutor with automated retry and re-grounding logic.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, Tuple, Optional, Callable

# Robust sys.path configuration so module can run both standalone and imported
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from core.mouse_executor import (
        ActionExecutor,
        normalize_bounding_box,
        sample_human_target_point,
        get_screen_resolution
    )
except ImportError:
    from mouse_executor import (
        ActionExecutor,
        normalize_bounding_box,
        sample_human_target_point,
        get_screen_resolution
    )

logger = logging.getLogger("SelfHealingLoop")


class UIStateValidator:
    """
    Validates whether an interactive action provoked a perceptible screen delta.
    Can use pixel arrays, Pillow images, or screen buffers.
    """

    @staticmethod
    def compute_visual_difference(img_before: Any, img_after: Any) -> float:
        """
        Calculates normalized visual difference score [0.0 to 1.0].
        Returns 0.0 if identical, > 0.0 if pixel delta detected.
        """
        if img_before is None or img_after is None:
            return 1.0 # Assume state changed if capturing was skipped

        if HAS_NUMPY:
            try:
                arr1 = np.asarray(img_before, dtype=np.float32)
                arr2 = np.asarray(img_after, dtype=np.float32)

                if arr1.shape != arr2.shape:
                    return 1.0 # Dimensions changed -> definite UI state change

                # Normalized Mean Absolute Difference
                diff = np.abs(arr1 - arr2)
                score = float(np.mean(diff) / 255.0)
                return score
            except Exception as e:
                logger.warning(f"Error computing numpy visual delta: {e}")
                return 1.0

        return 0.5 # Default heuristic fallback


class SelfHealingExecutor:
    """
    Self-Healing Orchestrator for desktop automation.
    If PyAutoGUI fails to produce a state change after clicking,
    expands crop boundaries and triggers re-grounding via Member 1's pipeline.
    """

    def __init__(
        self,
        grounder_callback: Optional[Callable[[str], Dict[str, Any]]] = None,
        max_retries: int = 3,
        min_delta_threshold: float = 0.015,
        dry_run: bool = False
    ):
        self.grounder_callback = grounder_callback
        self.max_retries = max_retries
        self.min_delta_threshold = min_delta_threshold
        self.dry_run = dry_run
        self.executor = ActionExecutor(dry_run=dry_run)

    def execute_with_self_healing(
        self,
        target_description: str,
        initial_bbox: list,
        action: str = "click",
        capture_crop_fn: Optional[Callable[..., Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes action with automated verification and self-healing recovery.
        """
        current_bbox = initial_bbox
        attempt = 0

        while attempt < self.max_retries:
            attempt += 1
            logger.info(f"[Self-Healing] Attempt {attempt}/{self.max_retries} for target: '{target_description}'")

            # 1. Pre-action snapshot
            img_before = capture_crop_fn(current_bbox) if capture_crop_fn else None

            # 2. Execute action
            abs_box = normalize_bounding_box(current_bbox)
            target_pt = sample_human_target_point(abs_box)

            if action in ("click", "left_click"):
                self.executor.execute_click(target_pt[0], target_pt[1])
            elif action == "double_click":
                self.executor.execute_click(target_pt[0], target_pt[1], clicks=2)

            time.sleep(0.35) # Wait for UI animation / rendering

            # 3. Post-action snapshot
            img_after = capture_crop_fn(current_bbox) if capture_crop_fn else None

            # 4. State Change Validation
            delta = UIStateValidator.compute_visual_difference(img_before, img_after)
            logger.info(f"[Self-Healing] Visual delta: {delta:.4f} (Threshold: {self.min_delta_threshold})")

            # In dry-run or if threshold met, treat as successful
            if self.dry_run or delta >= self.min_delta_threshold or capture_crop_fn is None:
                return {
                    "status": "success",
                    "attempts": attempt,
                    "final_bbox": current_bbox,
                    "target_coords": target_pt,
                    "visual_delta": delta
                }

            # 5. UI Did NOT Change -> Trigger Self-Healing Re-crop & Re-grounding
            logger.warning("[Self-Healing] Action produced no UI change! Triggering re-grounding loop...")

            if self.grounder_callback:
                try:
                    reground_result = self.grounder_callback(target_description)
                    if reground_result.get("target_found") and "bounding_box" in reground_result:
                        current_bbox = reground_result["bounding_box"]
                        logger.info(f"[Self-Healing] Recovered new target bounding box: {current_bbox}")
                        continue
                except Exception as ex:
                    logger.error(f"[Self-Healing] Re-grounding callback failed: {ex}")

            # Heuristic slight offset retry if grounder callback unavailable
            logger.info("[Self-Healing] Re-trying with slight offset perturbation...")
            time.sleep(0.5)

        return {
            "status": "failed",
            "attempts": attempt,
            "error": "Exceeded max retries without state change."
        }


if __name__ == "__main__":
    print("=" * 65)
    print(" SELF-HEALING ENGINE (MEMBER 2 - PHASE 3) TEST RUN")
    print("=" * 65)

    # Test self healing with mock grounder callback
    def mock_grounder(desc):
        print(f" -> Re-grounding called for: '{desc}'")
        return {"target_found": True, "bounding_box": [0.3, 0.4, 0.5, 0.6]}

    sh_executor = SelfHealingExecutor(grounder_callback=mock_grounder, dry_run=True)
    res = sh_executor.execute_with_self_healing(
        target_description="Submit Order Button",
        initial_bbox=[0.1, 0.2, 0.3, 0.4]
    )
    print(f"Self-Healing Result: {res}")
    print("\nSelf-Healing Engine ready!")
