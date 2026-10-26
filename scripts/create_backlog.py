#!/usr/bin/env python3
"""Import backlog/backlog.json into GitHub Issues and a public GitHub Project.

Requirements:
  - GitHub CLI (`gh`) installed and logged in:  gh auth login
  - Project scope added:                         gh auth refresh -s project
  - Python 3.9+ (standard library only)

Usage:
  python3 scripts/create_backlog.py --repo brave-machangu/MediTrack --dry-run
  python3 scripts/create_backlog.py --repo brave-machangu/MediTrack

Safe to re-run: existing issues (matched by the "MT-xxx:" title prefix) are
left unchanged (so ticked checkboxes survive), and an existing project with the
same title is reused. After a spec change, pass --update to re-render the bodies
of existing issues from backlog.json (this resets their checkboxes). At the end the script counts the items on the board and
exits with an error if any issue is missing. Visibility is checked if the API
reports it; still open the board URL in a private window before saying it's public.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "backlog" / "backlog.json"

ROLE_NAMES = {
    "lead": "Lead",
    "backend": "Backend agent",
    "frontend": "Frontend agent",
    "platform": "Platform agent",
    "test": "Test agent",
    "reviewer": "Reviewer agent",
}

LABELS = {
    "role:lead": ("5319e7", "Owned by the human Lead"),
    "role:backend": ("1d76db", "Owned by the Backend agent"),
    "role:frontend": ("0e8a16", "Owned by the Frontend agent"),
    "role:platform": ("fbca04", "Owned by the Platform agent"),
    "role:test": ("c5def5", "Owned by the independent Test agent"),
    "role:reviewer": ("ededed", "Owned by the Reviewer agent"),
    "priority:P0": ("b60205", "Needed to pass"),
    "priority:P1": ("d93f0b", "Strongly recommended"),
    "priority:P2": ("c2e0c6", "Later"),
    "phase:0-spec": ("bfdadc", "Phase 0: specification"),
    "phase:1-build": ("bfdadc", "Phase 1: build"),
    "phase:2-ship": ("bfdadc", "Phase 2: integrate and ship"),
    "phase:3-operate": ("bfdadc", "Phase 3: operate"),
    "phase:later": ("bfdadc", "Not scheduled"),
    "contract-change": ("e99695", "Proposed change to api/openapi.yaml"),
    "incident": ("b60205", "Opened by the responder agent or during a drill"),
    "security": ("000000", "Security or privacy concern"),
}


class GhError(RuntimeError):
    pass


def gh(args: list[str], dry_run: bool = False, mutating: bool = True) -> str:
    """Run a gh command. In dry-run mode, mutating commands are printed, not run."""
    if dry_run and mutating:
        print("  [dry-run] gh " + " ".join(args))
        return ""
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise GhError(f"gh {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def issue_body(task: dict, numbers: dict[str, int]) -> str:
    def ref(task_id: str) -> str:
        return f"{task_id} (#{numbers[task_id]})" if task_id in numbers else task_id

    deps = ", ".join(ref(d) for d in task["depends_on"]) or "none"
    lines = [
        f"**Task:** {task['id']}  ",
        f"**Owner:** {ROLE_NAMES[task['role']]}  ",
        f"**Priority:** {task['priority']}  ·  **Phase:** {task['phase']}  ",
        f"**Depends on:** {deps}",
        "",
        "**Files this task may change**",
        "",
        *[f"- `{f}`" for f in task["files"]],
        "",
        "### Acceptance criteria",
        "",
        *[f"- [ ] {a}" for a in task["acceptance"]],
        "",
        "AC-xx / OPS-xx IDs refer to docs/acceptance-criteria.md and docs/operations.md.",
        "",
        "### Verification",
        "",
        "```bash",
        *task["verify"],
        "```",
        "",
        "### Agent checklist",
        "",
        f"- [ ] Comment `Starting {task['id']}` with a short plan",
        f"- [ ] Branch `{task['id'].lower()}-<short-name>`; commits start with `{task['id']}: `",
        "- [ ] Run the verification commands and paste the output in the PR",
        "- [ ] Open a PR with `Closes #<this issue>` using the PR template",
        "- [ ] Comment a hand-off note: done / not done / open questions",
    ]
    if task.get("notes"):
        lines += ["", f"**Notes:** {task['notes']}"]
    return "\n".join(lines)


TEMP_DIR = Path(tempfile.mkdtemp(prefix="meditrack-backlog-"))


def write_temp(text: str) -> str:
    handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", encoding="utf-8", dir=TEMP_DIR)
    handle.write(text)
    handle.close()
    return handle.name


def main() -> int:
    # Windows consoles default to a legacy code page that can't print "→"/"…".
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="OWNER/REPO, e.g. brave-machangu/MediTrack")
    parser.add_argument("--project-title", default="MediTrack")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without making them")
    parser.add_argument("--update", action="store_true",
                        help="Also re-render bodies of existing issues from backlog.json (resets checkboxes)")
    args = parser.parse_args()

    owner, repo_name = args.repo.split("/", 1)
    tasks = json.loads(BACKLOG.read_text(encoding="utf-8"))["tasks"]
    dry = args.dry_run

    print("Checking gh login…")
    gh(["auth", "status"], mutating=False)

    print("Creating/updating labels…")
    for name, (color, desc) in LABELS.items():
        gh(["label", "create", name, "--repo", args.repo, "--color", color, "--description", desc, "--force"], dry)

    print("Looking for existing MT-xxx issues…")
    existing_raw = gh(
        ["issue", "list", "--repo", args.repo, "--state", "all", "--limit", "500", "--json", "number,title,url"],
        mutating=False,
    )
    existing = json.loads(existing_raw or "[]")
    numbers: dict[str, int] = {}
    urls: dict[str, str] = {}
    for issue in existing:
        match = re.match(r"^(MT-\d{3}):", issue["title"])
        if match:
            numbers[match.group(1)] = issue["number"]
            urls[match.group(1)] = issue["url"]

    print("Creating missing issues…")
    created_now: set[str] = set()
    for task in tasks:
        if task["id"] in numbers:
            print(f"  exists: {task['id']} → #{numbers[task['id']]}")
            continue
        labels = [f"role:{task['role']}", f"priority:{task['priority']}", f"phase:{task['phase']}"]
        body_file = write_temp(issue_body(task, numbers))
        cmd = ["issue", "create", "--repo", args.repo, "--title", f"{task['id']}: {task['title']}", "--body-file", body_file]
        for label in labels:
            cmd += ["--label", label]
        url = gh(cmd, dry)
        if url:
            numbers[task["id"]] = int(url.rstrip("/").split("/")[-1])
            urls[task["id"]] = url
            created_now.add(task["id"])
            print(f"  created: {task['id']} → {url}")

    to_render = set(created_now)
    if args.update:
        to_render |= {task["id"] for task in tasks if task["id"] in numbers}
    if to_render:
        print("Writing issue bodies (dependency links resolved)…")
        for task in tasks:
            if task["id"] in to_render:
                if dry:
                    print(f"  [dry-run] would update body of {task['id']}")
                    continue
                body_file = write_temp(issue_body(task, numbers))
                gh(["issue", "edit", str(numbers[task["id"]]), "--repo", args.repo, "--body-file", body_file])

    print("Finding or creating the project…")
    project_number = None
    project_url = None
    listing = json.loads(gh(["project", "list", "--owner", owner, "--closed", "--limit", "200", "--format", "json"], mutating=False) or "{}")
    projects = listing.get("projects", listing) if isinstance(listing, dict) else listing
    for project in projects or []:
        if project.get("title") == args.project_title:
            project_number, project_url = project.get("number"), project.get("url")
    if project_number is None:
        created = gh(["project", "create", "--owner", owner, "--title", args.project_title, "--format", "json"], dry)
        if created:
            data = json.loads(created)
            project_number, project_url = data.get("number"), data.get("url")

    failures: list[str] = []
    item_count = None
    visibility = "unknown"
    if project_number is not None and not dry:
        print(f"Adding issues to project #{project_number}…")
        for task in tasks:
            if task["id"] in urls:
                try:
                    gh(["project", "item-add", str(project_number), "--owner", owner, "--url", urls[task["id"]]])
                except GhError as err:
                    failures.append(task["id"])
                    print(f"  ERROR: could not add {task['id']}: {err}")
        gh(["project", "edit", str(project_number), "--owner", owner, "--visibility", "PUBLIC"])
        try:
            gh(["project", "link", str(project_number), "--owner", owner, "--repo", repo_name])
        except GhError as err:
            print(f"  note: link step reported: {err} (it may already be linked)")

        print("Verifying…")
        try:
            item_count = int(gh(["project", "item-list", str(project_number), "--owner", owner,
                                 "--limit", "500", "--format", "json", "--jq", ".items | length"], mutating=False))
        except (GhError, ValueError) as err:
            failures.append(f"could not count project items ({err})")
        try:
            public = gh(["project", "view", str(project_number), "--owner", owner, "--format", "json",
                         "--jq", ".public"], mutating=False)
            visibility = {"true": "PUBLIC", "false": "PRIVATE"}.get(public, "unknown")
        except GhError:
            visibility = "unknown"

    print("\nSummary")
    print(f"  issues on GitHub: {len(numbers)} of {len(tasks)} tasks")
    print(f"  project: {project_url or '(not created — dry run or error)'}")
    if not dry:
        print(f"  items on board: {item_count if item_count is not None else 'unknown'} (expected ≥ {len(tasks)})")
        print(f"  visibility reported by API: {visibility}")
        if item_count is not None and item_count < len(tasks):
            failures.append(f"board has {item_count} items, expected at least {len(tasks)}")
        if len(numbers) < len(tasks):
            failures.append(f"only {len(numbers)} of {len(tasks)} issues exist")
        if visibility == "PRIVATE":
            failures.append("project is still PRIVATE")
    for path in TEMP_DIR.glob("*.md"):
        path.unlink()
    TEMP_DIR.rmdir()
    if failures:
        print("\nNOT VERIFIED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    if not dry and project_url:
        print("\nNEXT: open the project URL in a private browser window to confirm it is public,")
        print("      then add the URL to README.md under 'Project board'.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GhError as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        print("Check `gh auth status` and that the token has the 'project' scope (gh auth refresh -s project).", file=sys.stderr)
        sys.exit(1)
