# src/ace_todo/gui.py
from __future__ import annotations
import tkinter as tk
import json
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from datetime import date, datetime, timedelta
import calendar
from typing import List, Dict, Optional

from ace_todo.storage import load_tasks, save_tasks

BASE = Path(__file__).resolve().parents[2]  # project root
STORE = BASE / "data"
TEMPLATE_FILE = BASE / "data" / "templates.json"


def load_templates() -> list[dict]:
    if TEMPLATE_FILE.exists():
        return json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
    return []

def save_templates(templates: list[dict]):
    TEMPLATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_FILE.write_text(json.dumps(templates, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------------- Date helpers ----------------
def parse_date(s: Optional[str]) -> Optional[date]:
    """
    Accepts:
      - YYYY-MM-DD
      - 'today' / 'tomorrow'
      - +N  (relative days)
    """
    if not s:
        return None
    s = s.strip().lower()
    if s == "today":
        return date.today()
    if s == "tomorrow":
        return date.today() + timedelta(days=1)
    if s.startswith("+") and s[1:].isdigit():
        return date.today() + timedelta(days=int(s[1:]))
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date. Use YYYY-MM-DD, 'today', 'tomorrow', or +N.")

def week_range(containing: date) -> tuple[date, date]:
    start = containing - timedelta(days=containing.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start, end

def due_as_date(t: Dict) -> Optional[date]:
    d = t.get("due")
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return None


# ---------------- Data helpers ----------------
def next_id(tasks: List[Dict]) -> int:
    return max((int(t.get("id", 0)) for t in tasks), default=0) + 1

def sorted_tasks(tasks: List[Dict]) -> List[Dict]:
    def key(t):
        d = due_as_date(t) or date.max
        return (d, bool(t.get("done")), int(t["id"]))
    return sorted(tasks, key=key)


# ---------------- GUI ----------------
class TodoGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ace TODO")
        self.geometry("760x520")
        self.minsize(720, 480)

        self._build_topbar()
        self._build_tree()
        self._build_buttons()

        self.refresh()

    def show_templates(self):
        templates = load_templates()
        win = tk.Toplevel(self)
        win.title("Templates")
        win.geometry("500x400")

        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # List rows: Name | [Copy]
        for tpl in templates:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=tpl["name"], width=20).pack(side=tk.LEFT)
            ttk.Button(row, text="Copy", command=lambda t=tpl["text"]: self.copy_to_clipboard(t)).pack(side=tk.RIGHT)

        ttk.Button(win, text="Add Template", command=lambda: self.add_template(win)).pack(side=tk.BOTTOM, pady=8)

    def copy_to_clipboard(self, text: str):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()  # keep it available after window closes
            messagebox.showinfo("Copied", "Template copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Clipboard error", str(e))

    def add_template(self, parent):
        name = simpledialog.askstring("Template Name", "Enter template name:", parent=parent)
        if not name:
            return
        text = simpledialog.askstring("Template Text", "Enter template text:", parent=parent)
        if text is None:
            return
        templates = load_templates()
        templates.append({"name": name.strip(), "text": text})
        save_templates(templates)
        messagebox.showinfo("Added", f"Template '{name}' added. Close and reopen Templates to see it.")

    

    # ----- UI sections -----
    def _build_topbar(self):
        bar = ttk.Frame(self)
        bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

        ttk.Label(bar, text="Title").grid(row=0, column=0, sticky="w")
        self.title_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.title_var, width=40).grid(row=0, column=1, sticky="we", padx=(4, 12))

        ttk.Label(bar, text="Due").grid(row=0, column=2, sticky="e")
        self.due_var = tk.StringVar()  # YYYY-MM-DD | today | tomorrow | +N
        ttk.Entry(bar, textvariable=self.due_var, width=16).grid(row=0, column=3, sticky="w", padx=(4, 12))

        ttk.Button(bar, text="Add", command=self.add_task).grid(row=0, column=4, padx=(4, 0))

        # Quick filters
        ttk.Button(bar, text="Today", command=self.filter_today).grid(row=0, column=5, padx=4)
        ttk.Button(bar, text="This Week", command=self.filter_week).grid(row=0, column=6, padx=4)
        ttk.Button(bar, text="Agenda…", command=self.filter_agenda).grid(row=0, column=7, padx=4)
        ttk.Button(bar, text="Calendar…", command=self.show_calendar).grid(row=0, column=8, padx=4)

        bar.columnconfigure(1, weight=1)

    def _build_tree(self):
        frame = ttk.Frame(self)
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=4)

        columns = ("id", "done", "due", "title")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("id", text="ID")
        self.tree.heading("done", text="Done")
        self.tree.heading("due", text="Due")
        self.tree.heading("title", text="Title")

        self.tree.column("id", width=50, anchor="e")
        self.tree.column("done", width=60, anchor="center")
        self.tree.column("due", width=100, anchor="center")
        self.tree.column("title", width=420, anchor="w")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    def _build_buttons(self):
        bar = ttk.Frame(self)
        bar.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=8)

        ttk.Button(bar, text="Mark Done", command=self.mark_done).pack(side=tk.LEFT)
        ttk.Button(bar, text="Remove", command=self.remove_tasks).pack(side=tk.LEFT, padx=8)

        ttk.Separator(bar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(bar, text="Set Due…", command=self.set_due).pack(side=tk.LEFT)
        ttk.Button(bar, text="Clear Due", command=self.clear_due).pack(side=tk.LEFT, padx=8)

        ttk.Separator(bar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side=tk.LEFT)

        ttk.Separator(bar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(bar, text="Templates", command=self.show_templates).pack(side=tk.LEFT)        

    # ----- Actions -----
    def refresh(self):
        tasks = load_tasks(STORE)
        tasks = sorted_tasks(tasks)
        self.tree.delete(*self.tree.get_children())
        for t in tasks:
            self.tree.insert("", tk.END, iid=str(t["id"]), values=(
                t["id"],
                "✓" if t.get("done") else "",
                t.get("due") or "",
                t.get("title", ""),
            ))

    def add_task(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Missing title", "Please enter a task title.")
            return
        due_text = self.due_var.get().strip() or None
        try:
            due_d = parse_date(due_text) if due_text else None
        except ValueError as e:
            messagebox.showerror("Invalid due date", str(e))
            return

        tasks = load_tasks(STORE)
        t = {
            "id": next_id(tasks),
            "title": title,
            "done": False,
            "due": due_d.isoformat() if due_d else None,
        }
        tasks.append(t)
        save_tasks(STORE, tasks)
        self.title_var.set("")
        self.due_var.set("")
        self.refresh()

    def _selected_ids(self) -> List[int]:
        sel = self.tree.selection()
        return [int(self.tree.item(i, "values")[0]) for i in sel]

    def mark_done(self):
        ids = self._selected_ids()
        if not ids:
            messagebox.showinfo("No selection", "Select one or more tasks to mark as done.")
            return
        tasks = load_tasks(STORE)
        ids_set = set(ids)
        for t in tasks:
            if int(t["id"]) in ids_set:
                t["done"] = True
        save_tasks(STORE, tasks)
        self.refresh()

    def remove_tasks(self):
        ids = self._selected_ids()
        if not ids:
            messagebox.showinfo("No selection", "Select one or more tasks to remove.")
            return
        if not messagebox.askyesno("Confirm remove", f"Remove {len(ids)} task(s)?"):
            return
        tasks = load_tasks(STORE)
        ids_set = set(ids)
        kept = [t for t in tasks if int(t["id"]) not in ids_set]
        save_tasks(STORE, kept)
        self.refresh()

    def set_due(self):
        ids = self._selected_ids()
        if len(ids) != 1:
            messagebox.showinfo("Select one", "Select exactly one task to set due.")
            return
        due_text = simpledialog.askstring("Set due date", "Enter due (YYYY-MM-DD | today | tomorrow | +N):", parent=self)
        if due_text is None:
            return
        try:
            d = parse_date(due_text)
        except ValueError as e:
            messagebox.showerror("Invalid due date", str(e))
            return

        tasks = load_tasks(STORE)
        for t in tasks:
            if int(t["id"]) == ids[0]:
                t["due"] = d.isoformat() if d else None
                break
        save_tasks(STORE, tasks)
        self.refresh()

    def clear_due(self):
        ids = self._selected_ids()
        if len(ids) != 1:
            messagebox.showinfo("Select one", "Select exactly one task to clear due.")
            return
        tasks = load_tasks(STORE)
        for t in tasks:
            if int(t["id"]) == ids[0]:
                t["due"] = None
                break
        save_tasks(STORE, tasks)
        self.refresh()

    # ----- Filters -----
    def filter_today(self):
        today = date.today()
        self._filter_range(today, today, title=f"Tasks due Today ({today})")

    def filter_week(self):
        start, end = week_range(date.today())
        self._filter_range(start, end, title=f"Tasks due This Week ({start}..{end})")

    def filter_agenda(self):
        start_s = simpledialog.askstring("Agenda", "Start date (YYYY-MM-DD | today | +N):", parent=self) or ""
        end_s = simpledialog.askstring("Agenda", "End date (YYYY-MM-DD | tomorrow | +N):", parent=self) or ""
        try:
            start = parse_date(start_s) if start_s else None
            end = parse_date(end_s) if end_s else None
            if start and end and end < start:
                messagebox.showerror("Invalid range", "End must be on/after start.")
                return
        except ValueError as e:
            messagebox.showerror("Invalid date", str(e))
            return
        self._filter_range(start, end, title=f"Agenda ({start or '...'}..{end or '...'})")

    def _filter_range(self, start: Optional[date], end: Optional[date], title: str):
        tasks = load_tasks(STORE)
        out: List[Dict] = []
        for t in tasks:
            d = due_as_date(t)
            if d is None:
                continue
            if start and d < start:
                continue
            if end and d > end:
                continue
            if not t.get("done"):
                out.append(t)
        out = sorted_tasks(out)

        # Show in a popup table
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("620x360")
        cols = ("id", "due", "title")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c, w in zip(cols, (60, 100, 400)):
            tree.heading(c, text=c.upper())
            tree.column(c, width=w, anchor=("e" if c == "id" else "w"))
        for t in out:
            tree.insert("", tk.END, values=(t["id"], t.get("due") or "", t.get("title", "")))
        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # ----- Calendar -----
    def show_calendar(self):
        # Month to display
        today = date.today()
        self._cal_month = date(today.year, today.month, 1)
        self._open_calendar_window()

    def _open_calendar_window(self):
        # If reopened, create a new popup
        win = tk.Toplevel(self)
        win.title("Calendar")
        win.geometry("420x340")
        self._cal_win = win

        top = ttk.Frame(win)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        self._cal_title = tk.StringVar()
        ttk.Button(top, text="◀", width=3, command=self._cal_prev).pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self._cal_title, font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, expand=True)
        ttk.Button(top, text="▶", width=3, command=self._cal_next).pack(side=tk.RIGHT)

        grid = ttk.Frame(win)
        grid.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Build calendar grid
        self._render_month(grid)

    def _render_month(self, grid: ttk.Frame):
        for child in grid.winfo_children():
            child.destroy()

        y, m = self._cal_month.year, self._cal_month.month
        self._cal_title.set(f"{calendar.month_name[m]} {y}")

        calendar.setfirstweekday(calendar.MONDAY)
        weeks = calendar.monthcalendar(y, m)

        # Collect counts
        tasks = load_tasks(STORE)
        counts: Dict[int, int] = {}
        for t in tasks:
            if t.get("done"):
                continue
            d = due_as_date(t)
            if d and d.year == y and d.month == m:
                counts[d.day] = counts.get(d.day, 0) + 1

        # Weekday header
        headers = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for c, h in enumerate(headers):
            ttk.Label(grid, text=h, anchor="center").grid(row=0, column=c, padx=2, pady=(0, 6), sticky="nsew")

        # Days
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    ttk.Label(grid, text="", width=6).grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                    continue
                count = counts.get(day, 0)
                txt = f"{day}" if count == 0 else f"{day} ({count})"
                btn = ttk.Button(grid, text=txt, width=8,
                                 command=lambda d=day: self._filter_day(y, m, d))
                btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

        for i in range(7):
            grid.columnconfigure(i, weight=1)
        for i in range(len(weeks) + 1):
            grid.rowconfigure(i, weight=1)

    def _filter_day(self, y: int, m: int, d: int):
        the_day = date(y, m, d)
        self._filter_range(the_day, the_day, title=f"Due on {the_day}")

    def _cal_prev(self):
        y, m = self._cal_month.year, self._cal_month.month
        if m == 1:
            y -= 1
            m = 12
        else:
            m -= 1
        self._cal_month = date(y, m, 1)
        self._render_month(self._cal_win.winfo_children()[1])  # re-render grid

    def _cal_next(self):
        y, m = self._cal_month.year, self._cal_month.month
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
        self._cal_month = date(y, m, 1)
        self._render_month(self._cal_win.winfo_children()[1])
    
    
def load_templates() -> list[dict]:
    if TEMPLATE_FILE.exists():
        return json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
    return []

def save_templates(templates: list[dict]):
    TEMPLATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_FILE.write_text(json.dumps(templates, indent=2, ensure_ascii=False), encoding="utf-8")

def show_templates(self):
    templates = load_templates()
    win = tk.Toplevel(self)
    win.title("Templates")
    win.geometry("500x400")

    frame = ttk.Frame(win)
    frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    for tpl in templates:
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=tpl["name"], width=20).pack(side=tk.LEFT)
        ttk.Button(row, text="Copy", command=lambda t=tpl["text"]: self.copy_to_clipboard(t)).pack(side=tk.RIGHT)

    ttk.Button(win, text="Add Template", command=lambda: self.add_template(win)).pack(side=tk.BOTTOM, pady=8)

def copy_to_clipboard(self, text: str):
    try:
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        messagebox.showinfo("Copied", "Template copied to clipboard.")
    except Exception as e:
        messagebox.showerror("Clipboard error", str(e))

def add_template(self, parent):
    name = simpledialog.askstring("Template Name", "Enter template name:", parent=parent)
    if not name:
        return
    text = simpledialog.askstring("Template Text", "Enter template text:", parent=parent)
    if text is None:
        return
    templates = load_templates()
    templates.append({"name": name.strip(), "text": text})
    save_templates(templates)
    messagebox.showinfo("Added", f"Template '{name}' added. Reopen Templates to see it.")



def main():
    app = TodoGUI()
    app.mainloop()


if __name__ == "__main__":
    main()