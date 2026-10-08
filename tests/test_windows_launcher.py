import os
import unittest

from core.command_planner import plan_command
from core.windows_launcher import choose_app, classify_command, find_file


class TestCommandRouting(unittest.TestCase):
    def test_app_open_commands(self):
        self.assertEqual(classify_command("Open spotify"), ("app", "spotify"))
        self.assertEqual(classify_command("Launch Brave Browser"), ("app", "Brave Browser"))
        self.assertEqual(classify_command("Open the Spotify app"), ("app", "Spotify"))
        self.assertEqual(classify_command("Open File Explorer"), ("app", "File Explorer"))

    def test_file_commands(self):
        self.assertEqual(classify_command("Open README.md"), ("file", "README.md"))
        self.assertEqual(classify_command("Find budget.xlsx"), ("file", "budget.xlsx"))
        self.assertEqual(classify_command("Open the budget file"), ("file", "budget"))

    def test_click_commands_stay_on_vision_path(self):
        self.assertIsNone(classify_command("Click the Save button"))
        self.assertIsNone(classify_command(""))

    def test_plans_real_actions_instead_of_search_paste(self):
        self.assertEqual(plan_command("Open spotify"), [{"action": "launch_app", "target": "spotify"}])
        self.assertEqual(plan_command("Open README.md"), [{"action": "open_file", "target": "README.md"}])
        self.assertEqual(plan_command("Close browser"), [{"action": "close_app", "target": "browser"}])
        self.assertEqual(
            plan_command("Open Notepad and type hello world"),
            [
                {"action": "launch_app", "target": "Notepad"},
                {"action": "type", "target": "hello world"},
            ],
        )
        self.assertEqual(
            plan_command("Click the Save button"),
            [{"action": "click", "target": "Save button"}],
        )

    def test_choose_app_prefers_exact_name(self):
        apps = [("Spotify", "id.spotify"), ("Spotify Free", "id.free"), ("Notepad", "id.notepad")]
        self.assertEqual(choose_app("Spotify", apps), ("Spotify", "id.spotify"))
        self.assertEqual(choose_app("note", apps)[0], "Notepad")

    def test_find_file_resolves_project_readme(self):
        path = find_file("README.md", roots=[os.getcwd()])
        self.assertTrue(path.lower().endswith("readme.md"))
        self.assertTrue(os.path.isfile(path))


if __name__ == "__main__":
    unittest.main()
