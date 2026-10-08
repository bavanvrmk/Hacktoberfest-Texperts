from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import os
from .roi_calculator import calculate_financial_roi
from .database_logger import DB_PATH

app = FastAPI(title="ROI & Compliance Dashboard")

# Ensure template directory exists
template_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(template_dir, exist_ok=True)

# Generate a minimal HTML template if it doesn't exist
template_file = os.path.join(template_dir, "dashboard.html")
if not os.path.exists(template_file):
    with open(template_file, "w") as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ROI Dashboard</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background-color: #0f172a; color: white; margin: 40px; }
                h1 { color: #3b82f6; }
                .card { background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { padding: 12px; border-bottom: 1px solid #334155; text-align: left; }
                th { background-color: #3b82f6; color: white; }
            </style>
        </head>
        <body>
            <h1>Automator ROI & Compliance Dashboard</h1>
            
            <div class="card">
                <h2>Financial ROI</h2>
                <p><strong>Cloud Costs Saved:</strong> ${{ roi.cloud_savings_usd }}</p>
                <p><strong>Human Hours Saved:</strong> {{ roi.hours_saved }} hrs</p>
                <p><strong>Labor Savings:</strong> ${{ roi.labor_savings_usd }}</p>
                <h3 style="color: #10b981;">Total Savings: ${{ roi.total_savings_usd }}</h3>
            </div>
            
            <div class="card">
                <h2>Execution Logs</h2>
                <table>
                    <tr>
                        <th>ID</th><th>Task Name</th><th>Start Time</th><th>Duration (ms)</th><th>Status</th>
                    </tr>
                    {% for row in logs %}
                    <tr>
                        <td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[4] }}</td><td>{{ row[5] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </body>
        </html>
        """)

templates = Jinja2Templates(directory=template_dir)

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM execution_logs ORDER BY id DESC LIMIT 50")
        logs = cursor.fetchall()
        
        # Count total tasks for ROI
        cursor.execute("SELECT COUNT(*) FROM execution_logs WHERE status='completed'")
        num_tasks = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        logs = []
        num_tasks = 0
        
    conn.close()
    
    roi_data = calculate_financial_roi(num_requests=num_tasks, num_automated_tasks=num_tasks)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "logs": logs,
        "roi": roi_data
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
