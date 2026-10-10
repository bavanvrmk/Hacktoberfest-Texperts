"""
Unit tests for WorkflowManager CRUD, ConfigManager, and Settings endpoints.
"""

import unittest
from core.workflow_manager import WorkflowManager
from core.config_manager import load_settings, save_settings, get_setting


class TestWorkflowManager(unittest.TestCase):
    def setUp(self):
        self.wm = WorkflowManager()

    def test_save_and_get_workflow(self):
        command = "open whatsapp and search for test contact and send hello"
        wf_id, steps = self.wm.save(command, name="Test WhatsApp Routine")
        self.assertIsNotNone(wf_id)
        self.assertTrue(len(steps) > 0)

        fetched = self.wm.get(wf_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["id"], wf_id)
        self.assertEqual(fetched["name"], "Test WhatsApp Routine")
        self.assertEqual(len(fetched["steps"]), len(steps))

    def test_update_workflow_steps(self):
        wf_id, steps = self.wm.save("Launch Notepad", name="Original Notepad")
        new_steps = [
            {"action": "launch_app", "target": "Notepad", "description": "Launch app"},
            {"action": "wait", "target": "1.0", "description": "Wait"},
            {"action": "type", "target": "Custom text", "description": "Type text"}
        ]
        updated = self.wm.update(wf_id, name="Renamed Routine", steps=new_steps)
        self.assertEqual(updated["name"], "Renamed Routine")
        self.assertEqual(len(updated["steps"]), 3)
        self.assertEqual(updated["steps"][2]["target"], "Custom text")

    def test_execute_workflow_details_saved(self):
        steps = [
            {"action": "test_echo", "target": "Hello World", "description": "Echo test"}
        ]
        wf_id, _ = self.wm.save("Test Echo Routine", steps=steps, name="Echo Routine")
        handlers = {
            "test_echo": lambda t: f"echoed_{t}"
        }
        res = self.wm.execute(wf_id, handlers)
        self.assertIn("echoed_Hello World", res)

        fetched = self.wm.get(wf_id)
        self.assertEqual(fetched["status"], "completed")
        self.assertEqual(fetched["steps"][0]["status"], "completed")
        self.assertEqual(fetched["steps"][0]["detail"], "echoed_Hello World")
        self.assertIsNotNone(fetched["steps"][0]["execution_time_ms"])

    def test_delete_workflow(self):
        wf_id, _ = self.wm.save("Temporary delete routine")
        self.wm.delete(wf_id)
        self.assertIsNone(self.wm.get(wf_id))


class TestConfigManager(unittest.TestCase):
    def test_load_and_save_settings(self):
        original = load_settings()
        self.assertIn("llama_server_url", original)

        save_settings({"mouse_speed": 0.42})
        self.assertEqual(get_setting("mouse_speed"), 0.42)

        # Restore original
        save_settings(original)


if __name__ == "__main__":
    unittest.main()
