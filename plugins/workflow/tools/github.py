#!/usr/bin/env python3
"""GitHub operations for PR and CI monitoring.

Usage:
    python github.py <command> [options]

Commands:
    my-prs [--repo REPO]            List my open PRs
    pr-checks <pr_number> [--repo]  Get CI checks for a PR
    pr-with-checks <pr_number>      Get PR details with CI status
    all-prs-status [--repo REPO]    Get all PRs with CI status
    failed-checks <pr_number>       Get failed checks for a PR
    ci-logs <pr_number> [--check]   Get CI failure logs
    pr-branch <pr_number>           Get branch name for PR

NOTE: To checkout a PR branch, use git.py checkout-worktree instead.
      Never checkout branches directly - always use worktrees.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path



@dataclass
class CICheck:
    """Represents a CI check status."""

    name: str
    status: str  # "success", "failure", "pending", "skipped"
    conclusion: str | None  # "success", "failure", "skipped", "cancelled", etc.
    url: str | None = None


@dataclass
class PullRequest:
    """Represents a GitHub pull request."""

    number: int
    title: str
    url: str
    branch: str
    base_branch: str
    state: str  # "open", "closed", "merged"
    repo: str = ""  # "owner/repo" format
    checks: list[CICheck] = field(default_factory=list)
    ci_status: str = "unknown"  # "passing", "failing", "pending"

    @property
    def is_ci_failing(self) -> bool:
        return self.ci_status == "failing"

    @property
    def is_ci_passing(self) -> bool:
        return self.ci_status == "passing"

    @property
    def display_name(self) -> str:
        """Short display name for the PR."""
        if self.repo:
            return f"{self.repo}#{self.number}"
        return f"#{self.number}"


def run_gh(args: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    """Run a gh CLI command."""
    try:
        result = subprocess.run(
            ["gh", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except FileNotFoundError:
        return False, "gh CLI not found. Install it from https://cli.github.com/"


def get_my_prs(cwd: Path | None = None, repo: str | None = None) -> list[PullRequest]:
    """Get all open PRs authored by the current user."""
    if repo:
        success, output = run_gh(
            [
                "pr",
                "list",
                "--repo",
                repo,
                "--author",
                "@me",
                "--state",
                "open",
                "--json",
                "number,title,url,headRefName,baseRefName,state",
            ],
            cwd,
        )
    else:
        success, output = run_gh(
            [
                "search",
                "prs",
                "--author",
                "@me",
                "--state",
                "open",
                "--json",
                "number,title,repository",
            ],
            cwd,
        )

    if not success:
        if "gh auth" in output.lower() or "authentication" in output.lower():
            print("GitHub CLI not authenticated.", file=sys.stderr)
            print("Run: gh auth login", file=sys.stderr)
        else:
            print(f"Failed to list PRs: {output}", file=sys.stderr)
        return []

    try:
        prs_data = json.loads(output)
    except json.JSONDecodeError:
        print("Failed to parse PR data", file=sys.stderr)
        return []

    prs = []
    for pr_data in prs_data:
        if "repository" in pr_data:
            repo_info = pr_data.get("repository", {})
            repo_name = repo_info.get("nameWithOwner", "unknown/unknown")
            branch = "unknown"
            base_branch = "main"
            url = f"https://github.com/{repo_name}/pull/{pr_data['number']}"
        else:
            repo_name = repo or "unknown"
            branch = pr_data.get("headRefName", "unknown")
            base_branch = pr_data.get("baseRefName", "main")
            url = pr_data.get("url", "")

        pr = PullRequest(
            number=pr_data["number"],
            title=pr_data["title"],
            url=url,
            branch=branch,
            base_branch=base_branch,
            state=pr_data.get("state", "open"),
            repo=repo_name,
        )
        prs.append(pr)

    return prs


def get_pr_checks(
    pr_number: int, cwd: Path | None = None, repo: str | None = None
) -> list[CICheck]:
    """Get CI checks status for a PR."""
    args = [
        "pr",
        "checks",
        str(pr_number),
        "--json",
        "name,state,link,workflow",
    ]
    if repo:
        args.extend(["--repo", repo])

    success, output = run_gh(args, cwd)

    if not success:
        return []

    try:
        checks_data = json.loads(output)
    except json.JSONDecodeError:
        return []

    checks = []
    for check_data in checks_data:
        state = check_data.get("state", "").upper()
        if state == "SUCCESS":
            conclusion = "success"
        elif state in ("FAILURE", "ERROR"):
            conclusion = "failure"
        elif state == "PENDING":
            conclusion = None
        else:
            conclusion = state.lower() if state else None

        check = CICheck(
            name=check_data.get("name", "unknown"),
            status=state.lower() if state else "unknown",
            conclusion=conclusion,
            url=check_data.get("link"),
        )
        checks.append(check)

    return checks


def get_pr_with_checks(
    pr_number: int, cwd: Path | None = None, repo: str | None = None
) -> PullRequest | None:
    """Get a PR with its CI check status."""
    args = [
        "pr",
        "view",
        str(pr_number),
        "--json",
        "number,title,url,headRefName,baseRefName,state",
    ]
    if repo:
        args.extend(["--repo", repo])

    success, output = run_gh(args, cwd)

    if not success:
        print(f"Failed to get PR #{pr_number}: {output}", file=sys.stderr)
        return None

    try:
        pr_data = json.loads(output)
    except json.JSONDecodeError:
        print("Failed to parse PR data", file=sys.stderr)
        return None

    pr = PullRequest(
        number=pr_data["number"],
        title=pr_data["title"],
        url=pr_data["url"],
        branch=pr_data["headRefName"],
        base_branch=pr_data["baseRefName"],
        state=pr_data["state"],
        repo=repo or "",
    )

    pr.checks = get_pr_checks(pr_number, cwd, repo)

    if not pr.checks:
        pr.ci_status = "unknown"
    elif any(c.conclusion == "failure" for c in pr.checks):
        pr.ci_status = "failing"
    elif any(c.status == "pending" or c.status == "in_progress" for c in pr.checks):
        pr.ci_status = "pending"
    elif all(
        c.conclusion in ("success", "skipped", "neutral") for c in pr.checks if c.conclusion
    ):
        pr.ci_status = "passing"
    else:
        pr.ci_status = "unknown"

    return pr


def get_all_prs_with_status(
    cwd: Path | None = None, repo: str | None = None
) -> list[PullRequest]:
    """Get all open PRs with their CI status."""
    prs = get_my_prs(cwd, repo)

    for pr in prs:
        pr.checks = get_pr_checks(pr.number, cwd, pr.repo or repo)

        if not pr.checks:
            pr.ci_status = "unknown"
        elif any(c.conclusion == "failure" for c in pr.checks):
            pr.ci_status = "failing"
        elif any(c.status == "pending" or c.status == "in_progress" for c in pr.checks):
            pr.ci_status = "pending"
        elif all(
            c.conclusion in ("success", "skipped", "neutral")
            for c in pr.checks
            if c.conclusion
        ):
            pr.ci_status = "passing"
        else:
            pr.ci_status = "unknown"

    return prs


def get_failed_checks(pr: PullRequest) -> list[CICheck]:
    """Get only the failed checks for a PR."""
    return [c for c in pr.checks if c.conclusion == "failure"]


def get_failed_ci_logs(
    pr_number: int,
    check_name: str | None = None,
    cwd: Path | None = None,
    repo: str | None = None,
) -> str:
    """Get the CI failure logs for a PR."""
    args = [
        "pr",
        "checks",
        str(pr_number),
        "--json",
        "name,state,link",
    ]
    if repo:
        args.extend(["--repo", repo])

    success, output = run_gh(args, cwd)

    if not success:
        return f"Failed to get checks: {output}"

    try:
        checks = json.loads(output)
    except json.JSONDecodeError:
        return "Failed to parse checks data"

    # gh pr checks uses "state" field with values like "FAILURE", "SUCCESS", etc.
    failed_checks = [c for c in checks if c.get("state", "").upper() in ("FAILURE", "ERROR")]

    if not failed_checks:
        return "No failed checks found"

    if check_name:
        failed_checks = [c for c in failed_checks if c.get("name") == check_name]
        if not failed_checks:
            return f"Check '{check_name}' not found or not failing"

    logs = []
    for check in failed_checks:
        details_url = check.get("link", "")
        check_name_str = check.get("name", "unknown")

        if "/actions/runs/" in details_url:
            try:
                run_id = details_url.split("/actions/runs/")[1].split("/")[0]

                run_args = ["run", "view", run_id, "--json", "jobs"]
                if repo:
                    run_args.extend(["--repo", repo])

                success, jobs_output = run_gh(run_args, cwd)

                if success:
                    jobs_data = json.loads(jobs_output)
                    failed_jobs = [
                        j
                        for j in jobs_data.get("jobs", [])
                        if j.get("conclusion") == "failure"
                    ]

                    for job in failed_jobs:
                        job_id = job.get("databaseId")
                        if job_id:
                            log_args = ["run", "view", "--job", str(job_id), "--log-failed"]
                            if repo:
                                log_args.extend(["--repo", repo])

                            success, log_output = run_gh(log_args, cwd)
                            if success and log_output:
                                logs.append(f"=== {check_name_str} - {job.get('name', 'unknown job')} ===")
                                logs.append(log_output)
                                logs.append("")
            except (IndexError, json.JSONDecodeError):
                pass

        if not logs:
            list_args = ["run", "list", "--branch", f"pr/{pr_number}", "--json", "databaseId,conclusion,name"]
            if repo:
                list_args.extend(["--repo", repo])

            success, runs_output = run_gh(list_args, cwd)

            if success:
                try:
                    runs = json.loads(runs_output)
                    failed_runs = [r for r in runs if r.get("conclusion") == "failure"]

                    for run in failed_runs[:3]:
                        run_id = run.get("databaseId")
                        if run_id:
                            view_args = ["run", "view", str(run_id), "--log-failed"]
                            if repo:
                                view_args.extend(["--repo", repo])

                            success, log_output = run_gh(view_args, cwd)
                            if success and log_output:
                                logs.append(f"=== {run.get('name', 'unknown')} ===")
                                logs.append(log_output)
                                logs.append("")
                except json.JSONDecodeError:
                    pass

    if not logs:
        return "Could not retrieve failure logs. Check the GitHub Actions UI directly."

    return "\n".join(logs)


def get_pr_branch(pr_number: int, cwd: Path | None = None, repo: str | None = None) -> str | None:
    """Get the branch name for a PR."""
    args = ["pr", "view", str(pr_number), "--json", "headRefName"]
    if repo:
        args.extend(["--repo", repo])
    success, output = run_gh(args, cwd)

    if not success:
        return None

    try:
        data = json.loads(output)
        return data.get("headRefName")
    except json.JSONDecodeError:
        return None


def pr_to_dict(pr: PullRequest) -> dict:
    """Convert PullRequest to dict."""
    return {
        "number": pr.number,
        "title": pr.title,
        "url": pr.url,
        "branch": pr.branch,
        "base_branch": pr.base_branch,
        "state": pr.state,
        "repo": pr.repo,
        "ci_status": pr.ci_status,
        "checks": [check_to_dict(c) for c in pr.checks],
    }


def check_to_dict(check: CICheck) -> dict:
    """Convert CICheck to dict."""
    return {
        "name": check.name,
        "status": check.status,
        "conclusion": check.conclusion,
        "url": check.url,
    }


# CLI Interface
def main():
    parser = argparse.ArgumentParser(description="GitHub CLI Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("my-prs", help="List my open PRs")
    p.add_argument("--repo", help="Filter by repo (owner/repo)")

    p = subparsers.add_parser("pr-checks", help="Get CI checks for a PR")
    p.add_argument("pr_number", type=int, help="PR number")
    p.add_argument("--repo", help="Repository (owner/repo)")

    p = subparsers.add_parser("pr-with-checks", help="Get PR with CI status")
    p.add_argument("pr_number", type=int, help="PR number")
    p.add_argument("--repo", help="Repository (owner/repo)")

    p = subparsers.add_parser("all-prs-status", help="Get all PRs with CI status")
    p.add_argument("--repo", help="Filter by repo (owner/repo)")

    p = subparsers.add_parser("failed-checks", help="Get failed checks for a PR")
    p.add_argument("pr_number", type=int, help="PR number")
    p.add_argument("--repo", help="Repository (owner/repo)")

    p = subparsers.add_parser("ci-logs", help="Get CI failure logs")
    p.add_argument("pr_number", type=int, help="PR number")
    p.add_argument("--check", help="Specific check name")
    p.add_argument("--repo", help="Repository (owner/repo)")

    p = subparsers.add_parser("pr-branch", help="Get branch name for PR")
    p.add_argument("pr_number", type=int, help="PR number")
    p.add_argument("--repo", help="Repository (owner/repo)")

    args = parser.parse_args()

    if args.command == "my-prs":
        prs = get_my_prs(repo=args.repo)
        print(json.dumps([pr_to_dict(pr) for pr in prs], indent=2))

    elif args.command == "pr-checks":
        checks = get_pr_checks(args.pr_number, repo=args.repo)
        print(json.dumps([check_to_dict(c) for c in checks], indent=2))

    elif args.command == "pr-with-checks":
        pr = get_pr_with_checks(args.pr_number, repo=args.repo)
        if pr:
            print(json.dumps(pr_to_dict(pr), indent=2))
        else:
            sys.exit(1)

    elif args.command == "all-prs-status":
        prs = get_all_prs_with_status(repo=args.repo)
        print(json.dumps([pr_to_dict(pr) for pr in prs], indent=2))

    elif args.command == "failed-checks":
        pr = get_pr_with_checks(args.pr_number, repo=args.repo)
        if pr:
            failed = get_failed_checks(pr)
            print(json.dumps([check_to_dict(c) for c in failed], indent=2))
        else:
            sys.exit(1)

    elif args.command == "ci-logs":
        logs = get_failed_ci_logs(args.pr_number, check_name=args.check, repo=args.repo)
        print(logs)

    elif args.command == "pr-branch":
        branch = get_pr_branch(args.pr_number, repo=args.repo)
        if branch:
            print(branch)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
