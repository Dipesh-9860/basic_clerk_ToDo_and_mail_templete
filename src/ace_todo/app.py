# src/ace_todo/app.py
import argparse
import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Dict, Optional

from ace_todo.storage import load_tasks, save_tasks

# project root is two levels up: .../Ace_TODO/src/ace_todo/app.py
BASE = Path(__file__).resolve().parents[2]
STORE = BASE / "data"


# ---------- Helpers ----------
def _next_id(tasks: List[Dict]) -> int:
    return max((t.get("id", 0) for t in tasks), default=0) + 1


def _parse_date(s: Optional[str]) -> Optional[date]:
    """
    Accepts:
      - YYYY-MM-DD  (preferred)
      - 'today' / 'tomorrow'
      - +N (days from today), e.g., +3
    Returns a date object or None.
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
        # Strict ISO format
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"Invalid date format: {s}. Use YYYY-MM-DD, 'today', 'tomorrow', or +N")


def _fmt_due(d: Optional[str]) -> str:
    return d or ""


def _task_due_as_date(t: Dict) -> Optional[date]:
    d = t.get("due")
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return None


def _is_done(t: Dict) -> bool:
    return bool(t.get("done"))


def _print_list(tasks: List[Dict]):
    if not tasks:
        print("(no tasks)")
        return
    print(f"{'ID':>3}  {'Done':4}  {'Due':10}  Title")
    print("-" * 60)
    for t in tasks:
        done = "✓" if _is_done(t) else ""
        print(f"{t['id']:>3}  {done:4}  {_fmt_due(t.get('due')):10}  {t.get('title', '')}")


def _filter_by_due_range(tasks: List[Dict], start: Optional[date], end: Optional[date],
                         include_done: bool = False) -> List[Dict]:
    out: List[Dict] = []
    for t in tasks:
        if not include_done and _is_done(t):
            continue
        d = _task_due_as_date(t)
        if d is None:
            continue
        if start and d < start:
            continue
        if end and d > end:
            continue
        out.append(t)
    # Sort by due, then id
    out.sort(key=lambda x: (_task_due_as_date(x) or date.max, x["id"]))
    return out


def _week_range(containing: date) -> tuple[date, date]:
    # Monday..Sunday of the week containing 'containing'
    start = containing - timedelta(days=containing.weekday())
    end = start + timedelta(days=6)
    return start, end


# ---------- Commands ----------
def cmd_add(args: argparse.Namespace):
    tasks = load_tasks(STORE)
    due_d = _parse_date(args.due) if args.due else None
    t = {
        "id": _next_id(tasks),
        "title": args.title.strip(),
        "done": False,
        "due": due_d.isoformat() if due_d else None,
    }
    tasks.append(t)
    save_tasks(STORE, tasks)
    print(f"✅ Added #{t['id']}: {t['title']}" + (f" (due {t['due']})" if t['due'] else ""))


def cmd_list(args: argparse.Namespace):
    tasks = load_tasks(STORE)
    items = tasks[:]

    if args.overdue:
        today = date.today()
        items = [t for t in items if not _is_done(t)
                 and _task_due_as_date(t) is not None
                 and _task_due_as_date(t) < today]

    if not args.all and not args.overdue:
        items = [t for t in items if not _is_done(t)]

    # Optional: sort by due then id (pending first)
    def sort_key(t):
        d = _task_due_as_date(t)
        return ((d or date.max), _is_done(t), t["id"])

    items.sort(key=sort_key)
    _print_list(items)


def cmd_done(args: argparse.Namespace):
    tasks = load_tasks(STORE)
    ids = set(int(x) for x in args.ids)
    for t in tasks:
        if t["id"] in ids:
            t["done"] = True
    save_tasks(STORE, tasks)
    print("✅ Marked done:", ", ".join(map(str, args.ids)))


def cmd_rm(args: argparse.Namespace):
    tasks = load_tasks(STORE)
    ids = set(int(x) for x in args.ids)
    kept = [t for t in tasks if t["id"] not in ids]
    save_tasks(STORE, kept)
    print("🗑️  Removed:", ", ".join(map(str, args.ids)))


def cmd_setdue(args: argparse.Namespace):
    tasks = load_tasks(STORE)
    tid = int(args.id)
    target = None
    for t in tasks:
        if t["id"] == tid:
            target = t
            break
    if not target:
        raise SystemExit(f"Task #{tid} not found")

    if args.clear:
        target["due"] = None
        print(f"🧹 Cleared due date for #{tid}")
    else:
        d = _parse_date(args.due)
        target["due"] = d.isoformat() if d else None
        print(f"🗓️  Set due for #{tid} -> {target['due']}")

    save_tasks(STORE, tasks)


def cmd_today(args: argparse.Namespace):
    tasks = load_tasks(STORE)
    today = date.today()
    items = _filter_by_due_range(tasks, today, today, include_done=args.all)
    print(f"📅 Today ({today.isoformat()}):")
    _print_list(items)


def cmd_week(args: argparse.Namespace):
    tasks = load_tasks(STORE)
    start, end = _week_range(date.today())
    items = _filter_by_due_range(tasks, start, end, include_done=args.all)
    print(f"📅 This week ({start.isoformat()} .. {end.isoformat()}):")
    _print_list(items)


def cmd_agenda(args: argparse.Namespace):
    tasks = load_tasks(STORE)
    start = _parse_date(args.start) if args.start else None
    end = _parse_date(args.end) if args.end else None
    if start and end and end < start:
        raise SystemExit("--end must be on/after --start")
    items = _filter_by_due_range(tasks, start, end, include_done=args.all)
    title = "📅 Agenda"
    if start or end:
        title += f" ({(start or '...')} .. {(end or '...')})"
    print(title)
    _print_list(items)


def cmd_cal(args: argparse.Namespace):
    """
    Render a month view with markers for number of pending tasks due on each day.
    Example: '12(2)' means 2 pending tasks due on the 12th.
    """
    # Resolve target month
    if args.month:
        try:
            y, m = args.month.split("-", 1)
            year, mon = int(y), int(m)
            target = date(year, mon, 1)
        except Exception:
            raise SystemExit("Use --month YYYY-MM (e.g., 2025-10)")
    else:
        today = date.today()
        target = date(today.year, today.month, 1)

    tasks = load_tasks(STORE)
    # Count pending tasks per day
    counts: Dict[int, int] = {}
    for t in tasks:
        if not args.all and _is_done(t):
            continue
        d = _task_due_as_date(t)
        if d and d.year == target.year and d.month == target.month:
            counts[d.day] = counts.get(d.day, 0) + 1

    cal = calendar.TextCalendar(firstweekday=0)  # Monday=0? In TextCalendar, 0=Mon if set; default 0=Mon
    # We will manually render to annotate cells
    weeks = calendar.monthcalendar(target.year, target.month)  # list of weeks, 0 means day from prev/next month
    header = f"{calendar.month_name[target.month]} {target.year}"
    print(header.center(28))
    print("Mo Tu We Th Fr Sa Su")

    # Adjust to Monday-first output explicitly
    cal.setfirstweekday(calendar.MONDAY)

    # Since monthcalendar uses current firstweekday, re-generate
    weeks = calendar.monthcalendar(target.year, target.month)

    for week in weeks:
        cells = []
        for day in week:
            if day == 0:
                cells.append("  ")
            else:
                c = counts.get(day, 0)
                if c == 0:
                    cells.append(f"{day:2d}")
                else:
                    # annotate with count in parentheses, but keep width 2-4
                    # e.g., 5(1) or 12(3)
                    mark = f"{day:2d}"
                    mark += f"({c})" if c < 10 else f"(9+)"
                    # trim/pad to max width 4 to keep columns aligned
                    cells.append(mark[:4])
        # Join with spaces, keep alignment: if short, pad
        line = ""
        for cell in cells:
            # each cell width 4 including trailing space
            line += cell.ljust(4)
        print(line.rstrip())


# ---------- Parser ----------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="todo", description="Simple To‑Do CLI with calendar features")
    sub = p.add_subparsers(dest="cmd", required=True)

    # add
    a = sub.add_parser("add", help="Add a new task")
    a.add_argument("title")
    a.add_argument("--due", help="YYYY-MM-DD | today | tomorrow | +N", default=None)
    a.set_defaults(func=cmd_add)

    # list
    l = sub.add_parser("list", help="List tasks")
    l.add_argument("--all", action="store_true", help="include done")
    l.add_argument("--overdue", action="store_true", help="only overdue pending tasks")
    l.set_defaults(func=cmd_list)

    # done
    d = sub.add_parser("done", help="Mark one or more tasks as done")
    d.add_argument("ids", nargs="+")
    d.set_defaults(func=cmd_done)

    # remove
    r = sub.add_parser("rm", help="Remove one or more tasks by ID")
    r.add_argument("ids", nargs="+")
    r.set_defaults(func=cmd_rm)

    # setdue
    sd = sub.add_parser("setdue", help="Set or clear a task's due date")
    sd.add_argument("id")
    grp = sd.add_mutually_exclusive_group(required=True)
    grp.add_argument("--due", help="YYYY-MM-DD | today | tomorrow | +N")
    grp.add_argument("--clear", action="store_true", help="remove due date")
    sd.set_defaults(func=cmd_setdue)

    # today
    t = sub.add_parser("today", help="Show tasks due today")
    t.add_argument("--all", action="store_true", help="include done")
    t.set_defaults(func=cmd_today)

    # week
    w = sub.add_parser("week", help="Show tasks due this week (Mon..Sun)")
    w.add_argument("--all", action="store_true", help="include done")
    w.set_defaults(func=cmd_week)

    # agenda (range)
    ag = sub.add_parser("agenda", help="Show tasks due in a date range")
    ag.add_argument("--start", help="YYYY-MM-DD | today | +N", default=None)
    ag.add_argument("--end", help="YYYY-MM-DD | tomorrow | +N", default=None)
    ag.add_argument("--all", action="store_true", help="include done")
    ag.set_defaults(func=cmd_agenda)

    # calendar
    c = sub.add_parser("cal", help="Render a month calendar with due tasks")
    c.add_argument("--month", help="YYYY-MM (defaults to current month)")
    c.add_argument("--all", action="store_true", help="include done in day counts")
    c.set_defaults(func=cmd_cal)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()