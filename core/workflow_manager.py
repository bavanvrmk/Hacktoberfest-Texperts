"""
Workflow Manager Module
Saves, updates, and executes autonomous desktop automation routines.
Maintains granular step states, execution durations, and step outputs in SQLite.
"""

import sqlite3
import time
from datetime import datetime

from core.command_planner import plan_command, compile_customer_intent_workflow
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
            command TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            updated_at TEXT,
            created_at TEXT,
            execution_notes TEXT
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
            description TEXT,
            execution_time_ms REAL,
            FOREIGN KEY (workflow_id) REFERENCES workflows(id)
        )
        """
    )
    # Check if new columns exist, and add if needed
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(workflow_steps)")
        cols = [col[1] for col in cursor.fetchall()]
        if "description" not in cols:
            conn.execute("ALTER TABLE workflow_steps ADD COLUMN description TEXT")
        if "execution_time_ms" not in cols:
            conn.execute("ALTER TABLE workflow_steps ADD COLUMN execution_time_ms REAL")
    except Exception as e:
        print(f"[WorkflowManager] DB migration check: {e}")

    try:
        cursor.execute("PRAGMA table_info(workflows)")
        w_cols = [col[1] for col in cursor.fetchall()]
        if "created_at" not in w_cols:
            conn.execute("ALTER TABLE workflows ADD COLUMN created_at TEXT")
        if "execution_notes" not in w_cols:
            conn.execute("ALTER TABLE workflows ADD COLUMN execution_notes TEXT")
    except Exception as e:
        print(f"[WorkflowManager] Workflows DB migration check: {e}")

    conn.commit()
    conn.close()


class WorkflowManager:
    def __init__(self):
        init_workflow_tables()

    def _compile_steps(self, command: str):
        """Intelligently compiles natural language command into structured steps."""
        try:
            from core.llm_client import LLMClient
            client = LLMClient()
            def _gen(prompt):
                res = client.chat_completion(
                    [{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=512,
                    timeout=20,
                )
                return res["choices"][0]["message"]["content"]
            steps = compile_customer_intent_workflow(command, _gen)
            if steps:
                return steps
        except Exception as exc:
            print(f"[WorkflowManager] Intent compiler fallback: {exc}")
        return plan_command(command)

    def save(self, command: str, steps=None, name=None, workflow_id=None):
        """
        Saves or updates a workflow and its ordered steps.
        If workflow_id is provided, updates that existing workflow.
        """
        cmd_clean = command.strip()
        if not steps:
            steps = self._compile_steps(cmd_clean)

        if not steps:
            raise RuntimeError("The command did not produce any automation steps.")

        now = datetime.now().isoformat(timespec="seconds")
        wf_name = (name or cmd_clean)[:80]

        conn = sqlite3.connect(DB_PATH)
        if workflow_id:
            conn.execute(
                "UPDATE workflows SET name = ?, command = ?, status = 'pending', updated_at = ? WHERE id = ?",
                (wf_name, cmd_clean, now, workflow_id),
            )
            conn.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (workflow_id,))
            target_id = workflow_id
        else:
            row = conn.execute("SELECT id FROM workflows WHERE command = ?", (cmd_clean,)).fetchone()
            if row:
                target_id = row[0]
                conn.execute(
                    "UPDATE workflows SET name = ?, status = 'pending', updated_at = ? WHERE id = ?",
                    (wf_name, now, target_id),
                )
                conn.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (target_id,))
            else:
                cursor = conn.execute(
                    "INSERT INTO workflows (name, command, status, updated_at, created_at) VALUES (?, ?, 'pending', ?, ?)",
                    (wf_name, cmd_clean, now, now),
                )
                target_id = cursor.lastrowid

        for index, step in enumerate(steps, start=1):
            action = step.get("action", "").strip()
            target = step.get("target", "") or ""
            desc = step.get("description", f"{action} {target}").strip()
            conn.execute(
                """
                INSERT INTO workflow_steps (workflow_id, position, action, target, status, description, detail)
                VALUES (?, ?, ?, ?, 'pending', ?, '')
                """,
                (target_id, index, action, target, desc),
            )
        conn.commit()
        conn.close()
        return target_id, steps

    def update(self, workflow_id: int, name: str = None, command: str = None, steps: list = None):
        """Edits an existing workflow's name, command, and steps."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        existing = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if not existing:
            conn.close()
            raise RuntimeError(f"Workflow #{workflow_id} does not exist.")

        now = datetime.now().isoformat(timespec="seconds")
        wf_name = name.strip() if name else existing["name"]
        wf_cmd = command.strip() if command else existing["command"]

        conn.execute(
            "UPDATE workflows SET name = ?, command = ?, updated_at = ? WHERE id = ?",
            (wf_name, wf_cmd, now, workflow_id),
        )

        if steps is not None:
            conn.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (workflow_id,))
            for index, step in enumerate(steps, start=1):
                action = step.get("action", "").strip()
                target = step.get("target", "") or ""
                desc = step.get("description", f"{action} {target}").strip()
                detail = step.get("detail", "")
                conn.execute(
                    """
                    INSERT INTO workflow_steps (workflow_id, position, action, target, status, description, detail)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?)
                    """,
                    (workflow_id, index, action, target, desc, detail),
                )

        conn.commit()
        conn.close()
        return self.get(workflow_id)

    def delete(self, workflow_id: int):
        """Deletes a workflow and all associated steps."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (workflow_id,))
        conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        conn.commit()
        conn.close()
        return True

    def get(self, workflow_id: int):
        """Returns single workflow with all ordered steps."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        workflow = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if not workflow:
            conn.close()
            return None
        steps = conn.execute(
            "SELECT * FROM workflow_steps WHERE workflow_id = ? ORDER BY position",
            (workflow_id,),
        ).fetchall()
        conn.close()
        return {
            "id": workflow["id"],
            "name": workflow["name"],
            "command": workflow["command"],
            "status": workflow["status"],
            "updated_at": workflow["updated_at"],
            "created_at": workflow["created_at"] if "created_at" in workflow.keys() else None,
            "execution_notes": workflow["execution_notes"] if "execution_notes" in workflow.keys() else None,
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
        """Lists all workflows ordered by most recently updated."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM workflows ORDER BY id DESC LIMIT 50").fetchall()
        result = []
        for row in rows:
            steps = conn.execute(
                "SELECT id, position, action, target, status, detail, description, execution_time_ms FROM workflow_steps WHERE workflow_id = ? ORDER BY position",
                (row["id"],),
            ).fetchall()
            result.append({
                "id": row["id"],
                "name": row["name"],
                "command": row["command"],
                "status": row["status"],
                "updated_at": row["updated_at"],
                "created_at": row["created_at"] if "created_at" in row.keys() else None,
                "execution_notes": row["execution_notes"] if "execution_notes" in row.keys() else None,
                "steps": [dict(step) for step in steps],
            })
        conn.close()
        return result

    def execute(self, workflow_id: int, handlers: dict, visual_thinker=None):
        """
        Executes all steps of workflow_id in order, saving execution time and
        output details for every step.
        """
        workflow = self.get(workflow_id)
        if not workflow:
            raise RuntimeError(f"Workflow {workflow_id} does not exist.")

        self._set_workflow_status(workflow_id, "running")
        summaries = []
        total = len(workflow["steps"])

        for step in workflow["steps"]:
            label = step.get("description") or _step_label(step)
            event_bus.emit(EVENT_PROGRESS, {
                "step": f"Step {step['position']}/{total}: {label}",
                "progress": step["position"] / max(total, 1),
            })
            self._set_step(step["id"], "running", "")
            action = step["action"]
            t0 = time.time()
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

                duration_ms = round((time.time() - t0) * 1000, 1)
                self._set_step(step["id"], "completed", str(detail), duration_ms=duration_ms)
                summaries.append(f"{label} ({detail})")
                print(f"[Workflow] Step #{step['position']} {label} -> {detail} ({duration_ms}ms)")

                # Multi-screenshot visual thinking loop between steps
                if visual_thinker:
                    try:
                        visual_thinker(step, step["position"], total)
                    except Exception as th_err:
                        print(f"[Workflow] Visual thinker note: {th_err}")

            except Exception as exc:
                duration_ms = round((time.time() - t0) * 1000, 1)
                err_msg = str(exc)
                self._set_step(step["id"], "failed", err_msg, duration_ms=duration_ms)
                self._set_workflow_status(workflow_id, "failed", notes=f"Failed at step {step['position']}: {err_msg}")
                raise

        final_summary = "; ".join(summaries)
        self._set_workflow_status(workflow_id, "completed", notes=final_summary)
        return final_summary

    def _set_workflow_status(self, workflow_id, status, notes=None):
        conn = sqlite3.connect(DB_PATH)
        now = datetime.now().isoformat(timespec="seconds")
        if notes is not None:
            conn.execute(
                "UPDATE workflows SET status = ?, updated_at = ?, execution_notes = ? WHERE id = ?",
                (status, now, notes, workflow_id),
            )
        else:
            conn.execute(
                "UPDATE workflows SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, workflow_id),
            )
        conn.commit()
        conn.close()

    def _set_step(self, step_id, status, detail, duration_ms=None):
        conn = sqlite3.connect(DB_PATH)
        if duration_ms is not None:
            conn.execute(
                "UPDATE workflow_steps SET status = ?, detail = ?, execution_time_ms = ? WHERE id = ?",
                (status, detail, duration_ms, step_id),
            )
        else:
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
