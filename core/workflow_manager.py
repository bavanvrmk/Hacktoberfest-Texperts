"""
Save a command as a workflow and run its steps in order.
"""

import sqlite3
from datetime import datetime

from core.command_planner import plan_command
from core.event_bus import event_bus, EVENT_PROGRESS
from src.architecture.database_logger import DB_PATH, init_db


def init_workflow_tables():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT NOT NULL UNIQUE,
            status TEXT DEFAULT 'pending',
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            action TEXT NOT NULL,
            target TEXT,
            status TEXT DEFAULT 'pending',
            detail TEXT,
            FOREIGN KEY (workflow_id) REFERENCES workflows(id)
        )
        """
    )
    conn.commit()
    conn.close()


class WorkflowManager:
    def __init__(self):
        init_workflow_tables()

    def save(self, command: str, steps=None):
        steps = steps or plan_command(command)
        if not steps:
            raise RuntimeError("The command did not contain anything to automate.")
        now = datetime.now().isoformat(timespec="seconds")
        name = command.strip()[:80]
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM workflows WHERE command = ?", (command.strip(),)).fetchone()
        if row:
            workflow_id = row[0]
            conn.execute(
                "UPDATE workflows SET name = ?, status = 'pending', updated_at = ? WHERE id = ?",
                (name, now, workflow_id),
            )
            conn.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (workflow_id,))
        else:
            cursor = conn.execute(
                "INSERT INTO workflows (name, command, status, updated_at) VALUES (?, ?, 'pending', ?)",
                (name, command.strip(), now),
            )
            workflow_id = cursor.lastrowid
        for index, step in enumerate(steps, start=1):
            conn.execute(
                """
                INSERT INTO workflow_steps (workflow_id, position, action, target, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (workflow_id, index, step["action"], step.get("target", "")),
            )
        conn.commit()
        conn.close()
        return workflow_id, steps

    def get(self, workflow_id: int):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        workflow = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        steps = conn.execute(
            "SELECT * FROM workflow_steps WHERE workflow_id = ? ORDER BY position",
            (workflow_id,),
        ).fetchall()
        conn.close()
        if not workflow:
            return None
        return {
            "id": workflow["id"],
            "name": workflow["name"],
            "command": workflow["command"],
            "status": workflow["status"],
            "updated_at": workflow["updated_at"],
            "steps": [dict(step) for step in steps],
        }

    def find(self, query: str):
        text = (query or "").strip()
        if text.isdigit():
            return self.get(int(text))
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id FROM workflows WHERE command = ? OR name LIKE ? ORDER BY id DESC LIMIT 1",
            (text, f"%{text}%"),
        ).fetchone()
        conn.close()
        return self.get(row["id"]) if row else None

    def list_workflows(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM workflows ORDER BY id DESC LIMIT 30").fetchall()
        result = []
        for row in rows:
            steps = conn.execute(
                "SELECT position, action, target, status, detail FROM workflow_steps WHERE workflow_id = ? ORDER BY position",
                (row["id"],),
            ).fetchall()
            result.append({
                "id": row["id"],
                "name": row["name"],
                "command": row["command"],
                "status": row["status"],
                "updated_at": row["updated_at"],
                "steps": [dict(step) for step in steps],
            })
        conn.close()
        return result

    def execute(self, workflow_id: int, handlers: dict, visual_thinker=None):
        workflow = self.get(workflow_id)
        if not workflow:
            raise RuntimeError(f"Workflow {workflow_id} does not exist.")
        self._set_workflow_status(workflow_id, "running")
        summaries = []
        total = len(workflow["steps"])
        for step in workflow["steps"]:
            label = _step_label(step)
            event_bus.emit(EVENT_PROGRESS, {
                "step": f"Step {step['position']}/{total}: {label}",
                "progress": step["position"] / max(total, 1),
            })
            self._set_step(step["id"], "running", "")
            action = step["action"]
            try:
                if action == "rerun":
                    found = self.find(step["target"])
                    if not found:
                        raise RuntimeError(f"No saved workflow matches '{step['target']}'.")
                    detail = self.execute(found["id"], handlers, visual_thinker=visual_thinker)
                else:
                    handler = handlers.get(action)
                    if handler is None:
                        raise RuntimeError(f"Unknown workflow action '{action}'.")
                    detail = handler(step.get("target") or "") or "done"
                self._set_step(step["id"], "completed", str(detail))
                summaries.append(f"{label} ({detail})")
                print(f"[Workflow] {label} -> {detail}")

                # Multi-screenshot visual thinking loop between steps
                if visual_thinker:
                    try:
                        visual_thinker(step, step["position"], total)
                    except Exception as th_err:
                        print(f"[Workflow] Visual thinker note: {th_err}")

            except Exception as exc:
                self._set_step(step["id"], "failed", str(exc))
                self._set_workflow_status(workflow_id, "failed")
                raise
        self._set_workflow_status(workflow_id, "completed")
        return "; ".join(summaries)

    def _set_workflow_status(self, workflow_id, status):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE workflows SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(timespec="seconds"), workflow_id),
        )
        conn.commit()
        conn.close()

    def _set_step(self, step_id, status, detail):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE workflow_steps SET status = ?, detail = ? WHERE id = ?",
            (status, detail, step_id),
        )
        conn.commit()
        conn.close()


def _step_label(step):
    action = step["action"].replace("_", " ")
    target = step.get("target") or ""
    return f"{action} {target}".strip()
