#!/usr/bin/env python3
"""Git operations for workflow orchestration using worktrees.

Usage:
    python git.py <command> [options]

Commands:
    repo-root                       Get repository root path
    repo-name                       Get repository name
    github-repo                     Get GitHub repo (owner/repo)
    main-branch                     Get main branch name (main/master)
    current-branch                  Get current branch name
    create-worktree <branch>        Create worktree for new branch
    checkout-worktree <branch>      Create worktree for existing remote branch
    remove-worktree <path>          Remove a worktree
    list-worktrees                  List all worktrees
    commit --message MSG            Stage and commit all changes
    push <branch>                   Push branch to remote
    create-pr --title T --body B    Create pull request
    changed-files [--base BRANCH]   List changed files vs base
    has-changes                     Check for uncommitted changes

IMPORTANT: Always use worktrees for branch work. Never checkout branches directly
in the main repository to avoid disrupting the user's working state.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


# Default worktree location (sibling to repo)
WORKTREE_BASE = ".worktrees"

# Repository search paths for auto-detecting repo locations
DEFAULT_REPO_PATHS = [Path.home() / "repos"]


def get_repo_search_paths() -> list[Path]:
    """Get the list of paths to search for repositories."""
    env_paths = os.environ.get("CLAUDE_WORKFLOW_REPO_PATHS")
    if env_paths:
        return [Path(p).expanduser() for p in env_paths.split(":") if p]
    return DEFAULT_REPO_PATHS


def run_git(args: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    """Run a git command."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()


def get_repo_root(cwd: Path | None = None) -> Path | None:
    """Get the git repository root directory."""
    success, output = run_git(["rev-parse", "--show-toplevel"], cwd)
    if success:
        return Path(output)
    return None


def get_repo_name(cwd: Path | None = None) -> str:
    """Get the repository name."""
    repo_root = get_repo_root(cwd)
    return repo_root.name if repo_root else "unknown"


def get_github_repo(cwd: Path | None = None) -> str | None:
    """Get the GitHub repo identifier (owner/repo) from git remote."""
    success, output = run_git(["remote", "get-url", "origin"], cwd)
    if not success:
        return None

    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", output)
    if match:
        return match.group(1)
    return None


def find_repo_directory(github_repo: str) -> Path | None:
    """Find the local directory for a GitHub repo."""
    if not github_repo:
        return None

    repo_name = github_repo.split("/")[-1]

    for base_path in get_repo_search_paths():
        if not base_path.exists():
            continue
        candidate = base_path / repo_name
        if candidate.exists() and candidate.is_dir():
            if (candidate / ".git").exists():
                return candidate
    return None


def get_main_branch(cwd: Path | None = None) -> str:
    """Detect the main branch name (main or master)."""
    success, _ = run_git(["rev-parse", "--verify", "main"], cwd)
    return "main" if success else "master"


def create_worktree(branch_name: str, cwd: Path | None = None) -> Path | None:
    """Create a git worktree for the branch."""
    repo_root = get_repo_root(cwd)
    if not repo_root:
        print("Not in a git repository", file=sys.stderr)
        return None

    main_branch = get_main_branch(cwd)

    print(f"  Fetching latest from origin/{main_branch}...", file=sys.stderr)
    run_git(["fetch", "origin", main_branch], repo_root)

    worktree_base = repo_root.parent / WORKTREE_BASE / repo_root.name
    worktree_path = worktree_base / branch_name.replace("/", "-")

    if worktree_path.exists():
        print("  Removing existing worktree...", file=sys.stderr)
        run_git(["worktree", "remove", "--force", str(worktree_path)], repo_root)

    print(
        f"  Creating worktree at {worktree_path.relative_to(repo_root.parent)}...", file=sys.stderr
    )
    success, output = run_git(
        [
            "worktree",
            "add",
            "-b",
            branch_name,
            str(worktree_path),
            f"origin/{main_branch}",
        ],
        repo_root,
    )

    if not success:
        success, output = run_git(
            ["worktree", "add", str(worktree_path), branch_name],
            repo_root,
        )

    if not success:
        print(f"Failed to create worktree: {output}", file=sys.stderr)
        return None

    print(f"Worktree: {worktree_path}", file=sys.stderr)
    print(f"Branch: {branch_name}", file=sys.stderr)

    return worktree_path


def create_worktree_for_existing_branch(
    branch_name: str, cwd: Path | None = None, repo: str | None = None
) -> Path | None:
    """Create a git worktree for an existing remote branch."""
    repo_root = get_repo_root(cwd)
    if not repo_root:
        print("Not in a git repository", file=sys.stderr)
        return None

    print(f"  Fetching branch {branch_name} from origin...", file=sys.stderr)
    success, _ = run_git(
        ["fetch", "origin", f"{branch_name}:{branch_name}"],
        repo_root,
    )
    if not success:
        run_git(["fetch", "origin"], repo_root)

    worktree_base = repo_root.parent / WORKTREE_BASE / repo_root.name
    worktree_path = worktree_base / f"ci-fix-{branch_name.replace('/', '-')}"

    if worktree_path.exists():
        print("  Removing existing worktree...", file=sys.stderr)
        run_git(["worktree", "remove", "--force", str(worktree_path)], repo_root)

    run_git(["worktree", "prune"], repo_root)

    print(
        f"  Creating worktree at {worktree_path.relative_to(repo_root.parent)}...", file=sys.stderr
    )

    success, output = run_git(
        ["worktree", "add", str(worktree_path), branch_name],
        repo_root,
    )

    if not success:
        success, output = run_git(
            [
                "worktree",
                "add",
                "--track",
                "-b",
                branch_name,
                str(worktree_path),
                f"origin/{branch_name}",
            ],
            repo_root,
        )

    if not success:
        success, output = run_git(
            ["worktree", "add", "--detach", str(worktree_path), f"origin/{branch_name}"],
            repo_root,
        )
        if success:
            run_git(["checkout", "-B", branch_name], worktree_path)
            run_git(["branch", "--set-upstream-to", f"origin/{branch_name}"], worktree_path)

    if not success:
        print(f"Failed to create worktree: {output}", file=sys.stderr)
        return None

    print(f"Worktree: {worktree_path}", file=sys.stderr)
    print(f"Branch: {branch_name}", file=sys.stderr)

    return worktree_path


def remove_worktree(worktree_path: Path, cwd: Path | None = None) -> bool:
    """Remove a git worktree."""
    repo_root = get_repo_root(cwd) or cwd
    success, output = run_git(
        ["worktree", "remove", "--force", str(worktree_path)],
        repo_root,
    )
    if success:
        print(f"Removed worktree: {worktree_path}", file=sys.stderr)
    return success


def list_worktrees(cwd: Path | None = None) -> list[dict]:
    """List all worktrees for the repository."""
    success, output = run_git(["worktree", "list", "--porcelain"], cwd)
    if not success:
        return []

    worktrees = []
    current: dict = {}

    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("branch "):
            current["branch"] = line[7:].replace("refs/heads/", "")

    if current:
        worktrees.append(current)

    return worktrees


def commit_changes(message: str, cwd: Path | None = None) -> bool:
    """Stage and commit all changes."""
    run_git(["add", "-A"], cwd)

    success, output = run_git(["status", "--porcelain"], cwd)
    if not output:
        print("No changes to commit", file=sys.stderr)
        return True

    full_message = f"""{message}

Generated with Claude Workflow Orchestrator

Co-Authored-By: Claude <noreply@anthropic.com>"""

    success, output = run_git(["commit", "-m", full_message], cwd)
    if not success:
        print(f"Failed to commit: {output}", file=sys.stderr)
        return False

    print("Changes committed", file=sys.stderr)
    return True


PROTECTED_BRANCHES = {"main", "master", "develop", "production", "staging"}


def push_branch(branch_name: str, cwd: Path | None = None) -> bool:
    """Push branch to remote."""
    if branch_name.lower() in PROTECTED_BRANCHES:
        print(
            f"BLOCKED: Cannot push directly to protected branch '{branch_name}'", file=sys.stderr
        )
        print("Create a feature branch and submit a PR instead.", file=sys.stderr)
        return False

    success, output = run_git(["push", "-u", "origin", branch_name], cwd)
    if not success:
        print(f"Failed to push: {output}", file=sys.stderr)
        return False
    print(f"Pushed branch: {branch_name}", file=sys.stderr)
    return True


def create_pr(title: str, body: str, cwd: Path | None = None) -> str | None:
    """Create a pull request using gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "pr", "create", "--title", title, "--body", body],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        pr_url = result.stdout.strip()
        print(f"Created PR: {pr_url}", file=sys.stderr)
        return pr_url
    except subprocess.CalledProcessError as e:
        print(f"Failed to create PR: {e.stderr}", file=sys.stderr)
        return None


def get_changed_files(base: str = "main", cwd: Path | None = None) -> list[str]:
    """Get list of changed files compared to base."""
    success, output = run_git(["diff", "--name-only", f"origin/{base}...HEAD"], cwd)
    if not success:
        success, output = run_git(["diff", "--name-only", f"{base}...HEAD"], cwd)
    return [f for f in output.split("\n") if f] if success else []


def get_current_branch(cwd: Path | None = None) -> str:
    """Get the current branch name."""
    success, output = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    return output if success else ""


def has_uncommitted_changes(cwd: Path | None = None) -> bool:
    """Check if there are any uncommitted changes."""
    run_git(["add", "-A"], cwd)
    success, output = run_git(["status", "--porcelain"], cwd)
    return bool(output.strip()) if success else False


# CLI Interface
def main():
    parser = argparse.ArgumentParser(description="Git CLI Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("repo-root", help="Get repository root path")
    subparsers.add_parser("repo-name", help="Get repository name")
    subparsers.add_parser("github-repo", help="Get GitHub repo (owner/repo)")
    subparsers.add_parser("main-branch", help="Get main branch name")
    subparsers.add_parser("current-branch", help="Get current branch name")
    subparsers.add_parser("list-worktrees", help="List all worktrees")
    subparsers.add_parser("has-changes", help="Check for uncommitted changes")

    p = subparsers.add_parser("create-worktree", help="Create worktree for NEW branch")
    p.add_argument("branch", help="Branch name")

    p = subparsers.add_parser(
        "checkout-worktree", help="Create worktree for EXISTING remote branch (e.g., for CI fixes)"
    )
    p.add_argument("branch", help="Existing branch name")
    p.add_argument("--repo", help="Repository path (defaults to cwd)")

    p = subparsers.add_parser("remove-worktree", help="Remove a worktree")
    p.add_argument("path", help="Worktree path")

    p = subparsers.add_parser("commit", help="Stage and commit all changes")
    p.add_argument("--message", "-m", required=True, help="Commit message")

    p = subparsers.add_parser("push", help="Push branch to remote")
    p.add_argument("branch", help="Branch name")

    p = subparsers.add_parser("create-pr", help="Create pull request")
    p.add_argument("--title", required=True, help="PR title")
    p.add_argument("--body", required=True, help="PR body")

    p = subparsers.add_parser("changed-files", help="List changed files")
    p.add_argument("--base", default="main", help="Base branch")

    args = parser.parse_args()

    if args.command == "repo-root":
        root = get_repo_root()
        print(str(root) if root else "")

    elif args.command == "repo-name":
        print(get_repo_name())

    elif args.command == "github-repo":
        repo = get_github_repo()
        print(repo if repo else "")

    elif args.command == "main-branch":
        print(get_main_branch())

    elif args.command == "current-branch":
        print(get_current_branch())

    elif args.command == "list-worktrees":
        worktrees = list_worktrees()
        print(json.dumps(worktrees, indent=2))

    elif args.command == "has-changes":
        has_changes = has_uncommitted_changes()
        print(json.dumps({"has_changes": has_changes}))
        sys.exit(0 if not has_changes else 1)

    elif args.command == "create-worktree":
        path = create_worktree(args.branch)
        if path:
            print(json.dumps({"path": str(path), "branch": args.branch}))
        else:
            sys.exit(1)

    elif args.command == "checkout-worktree":
        repo_path = Path(args.repo) if args.repo else None
        path = create_worktree_for_existing_branch(args.branch, cwd=repo_path)
        if path:
            print(json.dumps({"path": str(path), "branch": args.branch}))
        else:
            sys.exit(1)

    elif args.command == "remove-worktree":
        success = remove_worktree(Path(args.path))
        if not success:
            sys.exit(1)

    elif args.command == "commit":
        success = commit_changes(args.message)
        if not success:
            sys.exit(1)

    elif args.command == "push":
        success = push_branch(args.branch)
        if not success:
            sys.exit(1)

    elif args.command == "create-pr":
        url = create_pr(args.title, args.body)
        if url:
            print(json.dumps({"url": url}))
        else:
            sys.exit(1)

    elif args.command == "changed-files":
        files = get_changed_files(args.base)
        print(json.dumps(files, indent=2))


if __name__ == "__main__":
    main()
