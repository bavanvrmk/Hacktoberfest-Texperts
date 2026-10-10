"""
ROI Dashboard & Analytics Module (Member 4 Architecture Deliverable)
FastAPI web interface rendering real-time execution logs, cumulative cloud cost savings,
and live ROI calculations with auto-refresh.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import os
import sys
import threading

# Ensure root workspace is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.architecture.roi_calculator import calculate_financial_roi
from src.architecture.database_logger import DB_PATH, init_db

app = FastAPI(title="Shadow Automator - Live ROI & Compliance Dashboard")

# Ensure DB exists
init_db()

template_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(template_dir, exist_ok=True)
template_file = os.path.join(template_dir, "dashboard.html")

# Configure Jinja2 templates directory
templates = Jinja2Templates(directory=template_dir)

def get_stats_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM execution_logs ORDER BY id DESC LIMIT 100")
        logs = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM execution_logs WHERE status='completed'")
        num_tasks = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM execution_logs WHERE status='failed'")
        failed_tasks = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM execution_logs WHERE status='running'")
        running_tasks = cursor.fetchone()[0]
        cursor.execute("SELECT AVG(execution_time_ms) FROM execution_logs WHERE execution_time_ms IS NOT NULL AND status='completed'")
        avg_time = cursor.fetchone()[0] or 0
    except Exception:
        logs = []
        num_tasks = 0
        failed_tasks = 0
        running_tasks = 0
        avg_time = 0
    finally:
        conn.close()

    roi_data = calculate_financial_roi(num_requests=num_tasks, num_automated_tasks=num_tasks)
    stats_summary = {
        "total_executions": len(logs),
        "completed_count": num_tasks,
        "failed_count": failed_tasks,
        "running_count": running_tasks,
        "avg_duration_ms": round(avg_time, 1)
    }
    return logs, roi_data, stats_summary

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    from core.config_manager import load_settings
    logs, roi_data, stats_summary = get_stats_data()
    settings = load_settings()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request, 
            "logs": logs,
            "roi": roi_data,
            "stats": stats_summary,
            "settings": settings
        }
    )

@app.get("/api/stats", response_class=JSONResponse)
async def api_stats():
    logs, roi_data, stats_summary = get_stats_data()
    return {
        "logs": logs,
        "roi": roi_data,
        "stats": stats_summary
    }

@app.get("/api/system", response_class=JSONResponse)
async def api_system():
    return {
        "model_name": "Qwen2.5-VL-3B-Instruct (Q4_K_M)",
        "llama_server": "http://127.0.0.1:8080",
        "gpu_offload": "-ngl 99 (6GB VRAM Consumer GPU)",
        "context_window": "4096 tokens",
        "redaction_engine": "OpenCV Regex Masking (100% Offline)",
        "privacy_level": "Strict Zero Egress (Air-Gapped Ready)",
        "platform": "Windows 10/11 (DPI-Aware)"
    }

@app.get("/api/logs/{log_id}", response_class=JSONResponse)
async def api_get_log(log_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM execution_logs WHERE id = ?", (log_id,)).fetchone()
    conn.close()
    if not row:
        return JSONResponse({"error": "Log not found"}, status_code=404)
    return dict(row)

@app.get("/workflows", response_class=HTMLResponse)
async def workflows_page(request: Request):
    from core.workflow_manager import WorkflowManager
    from core.config_manager import load_settings
    workflows = WorkflowManager().list_workflows()
    settings = load_settings()
    return templates.TemplateResponse(
        request=request,
        name="workflows.html",
        context={
            "request": request,
            "workflows": workflows,
            "settings": settings
        }
    )

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    from core.config_manager import load_settings
    settings = load_settings()
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "request": request,
            "settings": settings
        }
    )

@app.get("/api/settings", response_class=JSONResponse)
async def api_get_settings():
    from core.config_manager import load_settings
    return load_settings()

@app.post("/api/settings", response_class=JSONResponse)
async def api_update_settings(payload: dict):
    from core.config_manager import save_settings
    try:
        updated = save_settings(payload)
        return {"ok": True, "settings": updated}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.post("/api/settings/test-llama", response_class=JSONResponse)
async def api_test_llama(payload: dict = None):
    import urllib.request
    from core.config_manager import get_setting
    url = (payload or {}).get("url") or get_setting("llama_server_url", "http://127.0.0.1:8080/v1")
    # Clean health or chat completion endpoint
    target = url.rstrip("/") + "/models" if "/v1" in url else url.rstrip("/") + "/health"
    try:
        req = urllib.request.Request(target, headers={"User-Agent": "ShadowAutomator/2.0"}, method="GET")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            status = resp.status
            return {"ok": True, "status": status, "target": target, "message": "Connected successfully to local vision engine"}
    except Exception as exc:
        return JSONResponse({"ok": False, "target": target, "error": str(exc)}, status_code=502)

@app.get("/api/workflows")
async def api_workflows():
    from core.workflow_manager import WorkflowManager
    return WorkflowManager().list_workflows()

@app.get("/api/workflows/{workflow_id}")
async def api_get_workflow(workflow_id: int):
    from core.workflow_manager import WorkflowManager
    wf = WorkflowManager().get(workflow_id)
    if not wf:
        return JSONResponse({"error": "Workflow not found"}, status_code=404)
    return wf

@app.post("/api/workflows")
async def api_create_workflow(payload: dict):
    from core.workflow_manager import WorkflowManager
    command = payload.get("command", "").strip()
    name = payload.get("name", "").strip() or None
    steps = payload.get("steps")
    if not command:
        return JSONResponse({"error": "Command string cannot be empty"}, status_code=400)
    try:
        wf_id, steps = WorkflowManager().save(command, steps=steps, name=name)
        return {"ok": True, "id": wf_id, "steps": steps}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.put("/api/workflows/{workflow_id}")
async def api_update_workflow(workflow_id: int, payload: dict):
    from core.workflow_manager import WorkflowManager
    name = payload.get("name")
    command = payload.get("command")
    steps = payload.get("steps")
    try:
        updated = WorkflowManager().update(workflow_id, name=name, command=command, steps=steps)
        return {"ok": True, "workflow": updated}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.delete("/api/workflows/{workflow_id}")
async def api_delete_workflow(workflow_id: int):
    from core.workflow_manager import WorkflowManager
    try:
        WorkflowManager().delete(workflow_id)
        return {"ok": True, "id": workflow_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.post("/api/workflows/{workflow_id}/run")
async def api_run_workflow(workflow_id: int):
    from core.workflow_manager import WorkflowManager
    from core.orchestrator import orchestrator
    workflow = WorkflowManager().get(workflow_id)
    if not workflow:
        return JSONResponse({"error": "workflow not found"}, status_code=404)
    threading.Thread(target=orchestrator.run_workflow_id, args=(workflow_id,), daemon=True).start()
    return {"ok": True, "id": workflow_id, "name": workflow["name"]}

@app.post("/api/spotlight/run")
async def api_spotlight_run(payload: dict):
    """Executes a command dispatched from Desktop or Web Spotlight Command Palette."""
    command = payload.get("command", "").strip()
    if not command:
        return JSONResponse({"error": "Command string cannot be empty"}, status_code=400)
    from core.orchestrator import orchestrator
    threading.Thread(target=orchestrator.run_pipeline, args=(command,), daemon=True).start()
    return {"ok": True, "command": command}

@app.get("/api/spotlight/suggestions")
async def api_spotlight_suggestions():
    """Returns curated presets and suggestions for Spotlight command palette."""
    return [
        {
            "id": "whatsapp_msg",
            "category": "APPS",
            "title": "WhatsApp: Send Message to Contact",
            "command": "open whatsapp and search for pranav cceb and send hi",
            "subtitle": "Search contact 'pranav cceb' & dispatch message via WhatsApp",
            "badge": "WhatsApp"
        },
        {
            "id": "screen_summary",
            "category": "VISION",
            "title": "Read & Summarize Screen Contents",
            "command": "read contents on the screen and summarize",
            "subtitle": "Local Qwen2.5-VL Vision reads active windows & summarizes",
            "badge": "Vision AI"
        },
        {
            "id": "open_twitter",
            "category": "APPS",
            "title": "Open Twitter / X in Browser",
            "command": "Open Twitter",
            "subtitle": "Launches https://x.com or native desktop client",
            "badge": "Web / App"
        },
        {
            "id": "open_chatgpt",
            "category": "APPS",
            "title": "Open ChatGPT Web Assistant",
            "command": "Open ChatGPT",
            "subtitle": "Launches https://chatgpt.com in default browser",
            "badge": "Web / AI"
        },
        {
            "id": "email_hackathon_demo",
            "category": "EMAIL",
            "title": "Send Email via Outlook to Evaluator",
            "command": "Send an email using outlook to jp_vedaj@cb.amrita.edu about how good my hackathon demo was",
            "subtitle": "Recipient: jp_vedaj@cb.amrita.edu · Topic: Hackathon Demo Feedback",
            "badge": "Outlook COM"
        },
        {
            "id": "roi_dashboard",
            "category": "TELEMETRY",
            "title": "Launch Live ROI & Financial Engine",
            "command": "Open Chrome and navigate to http://127.0.0.1:8000",
            "subtitle": "Real-time Telemetry, PII Audit Logs & Cost Metrics",
            "badge": "Browser"
        },
        {
            "id": "notepad_notes",
            "category": "APPS",
            "title": "Draft Presentation Notes in Notepad",
            "command": "Launch Notepad and type hackathon notes for jury evaluation",
            "subtitle": "Process Spawning & Sandboxed Keystroke Injection",
            "badge": "Windows App"
        },
        {
            "id": "vision_click",
            "category": "VISION",
            "title": "Autonomous Vision Grounding Click",
            "command": "Click the Save Changes button",
            "subtitle": "Local Qwen2.5-VL Object Detection & AR Projection",
            "badge": "Vision AI"
        },
        {
            "id": "taskmgr",
            "category": "SYSTEM",
            "title": "Inspect Desktop Performance & VRAM",
            "command": "Launch Task Manager",
            "subtitle": "Win32 Sandbox Process Monitor",
            "badge": "System"
        }
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
