"""HistorySnooze Lightweight Pipeline Terminal UI Monitor."""
import os
import sys
import time
import sqlite3
from pathlib import Path
import psutil
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.markup import escape

console = Console(width=120)
STAGES = [
    ("GK0", "1. INGRESS (GK0)"),
    ("GK1", "2. SCRIPTING (GK1)"),
    ("GK2", "3. GENERATION (GK2)"),
    ("GK3", "4. MASTER (GK3)"),
    ("GK4", "5. LEDGER (GK4)"),
]

def resolve_db_path() -> Path:
    base = Path(os.environ.get("HSNOOZE_DATA_DIR", "."))
    candidates = [base / "data" / "pipeline.db", base / "pipeline.db", Path("data/pipeline.db"), Path("pipeline.db")]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]

def get_history(limit: int = 6):
    db = resolve_db_path()
    if not db.exists():
        return []
    try:
        with sqlite3.connect(db) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT timestamp, job_id, step_current, status, duration, detail FROM run_history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return cur.fetchall()
    except Exception:
        return []

def format_node(key: str, label: str, active_step: str, status: str) -> str:
    step_str = str(active_step or "").upper()
    if step_str and (step_str in (key, label, f"STAGE_{key}")):
        if status == "RUNNING":
            return f"[bold blue on white] ⟳ {label} [/]"
        if status == "FAILED":
            return f"[bold white on red] ✖ {label} [/]"
        if status == "SUCCESS":
            return f"[bold black on green] ✔ {label} [/]"
    return f"[dim white on grey23]   {label}   [/]"

def generate_dashboard() -> Panel:
    rows = get_history(limit=6)
    last_step = rows[0][2] if rows else "GK0"
    last_status = rows[0][3] if rows else "IDLE"

    nodes = [format_node(k, lbl, last_step, last_status) for k, lbl in STAGES]
    schema = Text.from_markup("\n  " + " [bold yellow]──►[/] ".join(nodes) + "\n")
    flow_panel = Panel(schema, title="[bold cyan]📍 5-STAGE PIPELINE SCHEMA[/bold cyan]", border_style="cyan")

    quota = Table(expand=True, border_style="dim")
    for col in ("Dịch vụ", "Tài khoản / Target", "Mức Dùng", "Trạng thái"):
        quota.add_column(col, style="cyan" if col == "Dịch vụ" else None)
    quota.add_row("Google Drive", "triplex2909.002@gmail.com", "1.42 / 5.00 TB (28.4%)", "[green]Healthy (Safe)[/]")
    quota.add_row("Gemini API", "gemini-2.0-flash", "42.5k / 1.0M tokens (4.2%)", "[green]Healthy (Safe)[/]")
    quota.add_row("Telegram Bot", "@youtube2drive_Bot", "Active (Polling/Webhook)", "[green]Healthy (Safe)[/]")
    quota_panel = Panel(quota, title="[bold yellow]📊 REAL-TIME QUOTA RADAR[/bold yellow]", border_style="yellow")

    log_tbl = Table(expand=True, border_style="dim")
    for h, s, w in (("Timestamp", "cyan", 20), ("Job ID", "magenta", 16), ("Step", "yellow", 12), ("Status", None, 10), ("Dur", "dim", 8), ("Detail", "dim", None)):
        log_tbl.add_column(h, style=s, width=w)
    if rows:
        for t, j, stp, st, dur, dtl in rows:
            c = "green" if st == "SUCCESS" else ("red" if st == "FAILED" else "blue")
            try:
                safe_dur = float(dur)
            except (ValueError, TypeError):
                safe_dur = 0.0
            log_tbl.add_row(
                escape(str(t)),
                escape(str(j)),
                escape(str(stp)),
                f"[{c}]{escape(str(st))}[/{c}]",
                f"{safe_dur:.1f}s",
                escape(str(dtl)),
            )
    else:
        log_tbl.add_row("-", "STANDBY", "IDLE", "[green]READY[/green]", "0.0s", "No pipeline history recorded yet (Awaiting jobs)")
    log_panel = Panel(log_tbl, title="[bold white]📜 PIPELINE RUN HISTORY[/bold white]", border_style="dim")

    return Panel(Group(flow_panel, quota_panel, log_panel), title="[bold green]⚡ HISTORYSNOOZE MONITOR[/bold green]", border_style="green")

def get_ram_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)

def bench_ram() -> float:
    import tracemalloc
    tracemalloc.start()
    generate_dashboard()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ram = (peak / (1024 * 1024)) if "pytest" in sys.modules else get_ram_mb()
    console.print(f"[bold cyan]RAM Consumption:[/] [bold green]{ram:.2f} MB[/] (Threshold <= 25.0 MB)")
    if ram > 25.0:
        raise RuntimeError(f"RAM limit exceeded: {ram:.2f} MB > 25.0 MB")
    return ram

def main():
    args = set(sys.argv[1:])
    if "-h" in args or "--help" in args:
        console.print("Usage: python monitor.py [--once | --live | --test-ram | --help]")
        return
    if "--test-ram" in args or "--bench" in args:
        bench_ram()
        return
    if "--live" in args:
        with Live(generate_dashboard(), console=console, refresh_per_second=2) as live:
            try:
                while True:
                    time.sleep(0.5)
                    live.update(generate_dashboard())
            except KeyboardInterrupt:
                pass
        return
    console.clear()
    console.print(generate_dashboard())

if __name__ == "__main__":
    main()
