#!/usr/bin/env python3
"""Linear integration tools using direct GraphQL API.

Usage:
    python linear.py <command> [options]

Commands:
    get-ticket <ticket_id>          Get ticket details
    create-ticket --team TEAM --title TITLE [--description DESC] [--project ID] [--state STATE]
    update-status <ticket_id> --status STATUS
    add-comment <ticket_id> --body BODY
    get-project <project_id>        Get project details
    get-project-tickets <project_id> List tickets in a project
    create-project --team TEAM --name NAME [--description DESC]

Environment:
    LINEAR_API_KEY: Your Linear API key (required)
"""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass

import httpx

# Linear API configuration
LINEAR_API_URL = "https://api.linear.app/graphql"

# Linear Team IDs
LINEAR_TEAMS: dict[str, str] = {
    "staff": "f2bad003-335e-4f0a-bf1f-480e7bbaef48",
    "defects": "b9a271b1-7b8b-4d11-87cc-00cb71917ff0",
    "chapter-api": "1f085756-d37e-4067-a5d0-fefc88f42bb0",
    "sre": "2d9b40a6-92f2-4cf8-8fad-8f9bc0f80041",
}


def _get_api_key() -> str:
    """Get Linear API key from environment."""
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        raise ValueError(
            "LINEAR_API_KEY environment variable is required. "
            "Get your API key from Linear Settings > API > Personal API keys"
        )
    return api_key


def _get_headers() -> dict[str, str]:
    """Get headers for Linear API requests."""
    return {
        "Content-Type": "application/json",
        "Authorization": _get_api_key(),
    }


@dataclass
class LinearProject:
    """Represents a Linear project."""

    id: str
    name: str
    url: str
    description: str = ""


@dataclass
class LinearTicket:
    """Represents a Linear ticket."""

    id: str
    identifier: str  # e.g., "STAFF-123"
    title: str
    url: str
    status: str
    description: str = ""


class LinearAPIError(Exception):
    """Error from Linear API."""

    pass


async def _execute_query(query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query against Linear API."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            LINEAR_API_URL,
            json=payload,
            headers=_get_headers(),
        )

    if response.status_code != 200:
        raise LinearAPIError(f"API request failed: {response.status_code} - {response.text}")

    data = response.json()

    if "errors" in data:
        errors = data["errors"]
        error_messages = [e.get("message", str(e)) for e in errors]
        raise LinearAPIError(f"GraphQL errors: {', '.join(error_messages)}")

    return data.get("data", {})


# GraphQL Queries
ISSUE_FRAGMENT = """
fragment IssueFields on Issue {
    id
    identifier
    title
    description
    url
    state {
        id
        name
    }
}
"""

GET_ISSUE_QUERY = """
query GetIssue($id: String!) {
    issue(id: $id) {
        ...IssueFields
    }
}
""" + ISSUE_FRAGMENT

LIST_ISSUES_QUERY = """
query ListIssues($filter: IssueFilter) {
    issues(filter: $filter, first: 100) {
        nodes {
            ...IssueFields
        }
    }
}
""" + ISSUE_FRAGMENT

GET_PROJECT_QUERY = """
query GetProject($id: String!) {
    project(id: $id) {
        id
        name
        description
        url
    }
}
"""

LIST_PROJECT_ISSUES_QUERY = """
query ListProjectIssues($projectId: String!) {
    project(id: $projectId) {
        issues(first: 100) {
            nodes {
                ...IssueFields
            }
        }
    }
}
""" + ISSUE_FRAGMENT

SEARCH_PROJECTS_QUERY = """
query SearchProjects($query: String!) {
    projects(filter: { name: { containsIgnoreCase: $query } }, first: 10) {
        nodes {
            id
            name
            description
            url
        }
    }
}
"""

# GraphQL Mutations
CREATE_PROJECT_MUTATION = """
mutation CreateProject($input: ProjectCreateInput!) {
    projectCreate(input: $input) {
        success
        project {
            id
            name
            description
            url
        }
    }
}
"""

CREATE_ISSUE_MUTATION = """
mutation CreateIssue($input: IssueCreateInput!) {
    issueCreate(input: $input) {
        success
        issue {
            ...IssueFields
        }
    }
}
""" + ISSUE_FRAGMENT

UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
    issueUpdate(id: $id, input: $input) {
        success
        issue {
            ...IssueFields
        }
    }
}
""" + ISSUE_FRAGMENT

CREATE_COMMENT_MUTATION = """
mutation CreateComment($input: CommentCreateInput!) {
    commentCreate(input: $input) {
        success
        comment {
            id
            body
        }
    }
}
"""

GET_WORKFLOW_STATES_QUERY = """
query GetWorkflowStates($teamId: String!) {
    team(id: $teamId) {
        states {
            nodes {
                id
                name
                type
            }
        }
    }
}
"""


async def create_project(
    name: str,
    description: str,
    team: str = "staff",
) -> LinearProject:
    """Create a Linear project."""
    team_id = LINEAR_TEAMS.get(team, LINEAR_TEAMS["staff"])

    variables = {
        "input": {
            "name": name,
            "description": description,
            "teamIds": [team_id],
        }
    }

    try:
        data = await _execute_query(CREATE_PROJECT_MUTATION, variables)
        result = data.get("projectCreate", {})

        if result.get("success"):
            project = result.get("project", {})
            print(f"✓ Project created: {project.get('url', '')}", file=sys.stderr)
            return LinearProject(
                id=project.get("id", ""),
                name=project.get("name", name),
                url=project.get("url", ""),
                description=project.get("description", ""),
            )
        else:
            print("Failed to create project", file=sys.stderr)
            return LinearProject(id="", name=name, url="")
    except LinearAPIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        return LinearProject(id="", name=name, url="")


async def create_ticket(
    title: str,
    description: str,
    team: str = "staff",
    project_id: str | None = None,
    labels: list[str] | None = None,
    state: str | None = None,
) -> LinearTicket:
    """Create a Linear ticket."""
    team_id = LINEAR_TEAMS.get(team, LINEAR_TEAMS["staff"])

    input_data: dict = {
        "title": title,
        "description": description,
        "teamId": team_id,
    }

    if project_id:
        input_data["projectId"] = project_id

    if labels:
        input_data["labelIds"] = labels

    if state:
        state_id = await _get_state_id(team_id, state)
        if state_id:
            input_data["stateId"] = state_id

    try:
        data = await _execute_query(CREATE_ISSUE_MUTATION, {"input": input_data})
        result = data.get("issueCreate", {})

        if result.get("success"):
            issue = result.get("issue", {})
            state_info = issue.get("state", {})
            return LinearTicket(
                id=issue.get("id", ""),
                identifier=issue.get("identifier", ""),
                title=issue.get("title", title),
                url=issue.get("url", ""),
                status=state_info.get("name", "Backlog"),
                description=description,
            )
        else:
            print(f"Failed to create ticket '{title}'", file=sys.stderr)
            return LinearTicket(
                id="", identifier="", title=title, url="", status="Failed", description=""
            )
    except LinearAPIError as e:
        print(f"API Error creating ticket: {e}", file=sys.stderr)
        return LinearTicket(
            id="", identifier="", title=title, url="", status="Failed", description=""
        )


async def _get_state_id(team_id: str, state_name: str) -> str | None:
    """Get the state ID for a given state name."""
    try:
        data = await _execute_query(GET_WORKFLOW_STATES_QUERY, {"teamId": team_id})
        team = data.get("team", {})
        states = team.get("states", {}).get("nodes", [])

        for s in states:
            if s.get("name", "").lower() == state_name.lower():
                return s.get("id")
        return None
    except LinearAPIError:
        return None


async def update_ticket_status(
    ticket_id: str,
    status: str,
) -> bool:
    """Update a Linear ticket's status."""
    ticket = await get_ticket(ticket_id)
    if not ticket or not ticket.id:
        print(f"Could not find ticket: {ticket_id}", file=sys.stderr)
        return False

    state_id = None
    for team_id in LINEAR_TEAMS.values():
        state_id = await _get_state_id(team_id, status)
        if state_id:
            break

    if not state_id:
        print(f"Could not find state '{status}'", file=sys.stderr)
        return False

    try:
        data = await _execute_query(
            UPDATE_ISSUE_MUTATION,
            {"id": ticket.id, "input": {"stateId": state_id}},
        )
        result = data.get("issueUpdate", {})

        if result.get("success"):
            print(f"  Updated {ticket_id} → {status}", file=sys.stderr)
            return True
        else:
            print(f"Could not confirm status update for {ticket_id}", file=sys.stderr)
            return False
    except LinearAPIError as e:
        print(f"Error updating status: {e}", file=sys.stderr)
        return False


async def add_comment(
    ticket_id: str,
    comment: str,
) -> bool:
    """Add a comment to a Linear ticket."""
    ticket = await get_ticket(ticket_id)
    if not ticket or not ticket.id:
        print(f"Could not find ticket: {ticket_id}", file=sys.stderr)
        return False

    try:
        data = await _execute_query(
            CREATE_COMMENT_MUTATION,
            {"input": {"issueId": ticket.id, "body": comment}},
        )
        result = data.get("commentCreate", {})

        if result.get("success"):
            return True
        else:
            print(f"Could not confirm comment added to {ticket_id}", file=sys.stderr)
            return False
    except LinearAPIError as e:
        print(f"Error adding comment: {e}", file=sys.stderr)
        return False


async def get_ticket(ticket_id: str) -> LinearTicket | None:
    """Get a Linear ticket by ID or identifier."""
    try:
        data = await _execute_query(GET_ISSUE_QUERY, {"id": ticket_id})
        issue = data.get("issue")

        if not issue:
            print(f"Could not find ticket: {ticket_id}", file=sys.stderr)
            return None

        state_info = issue.get("state", {})
        return LinearTicket(
            id=issue.get("id", ""),
            identifier=issue.get("identifier", ""),
            title=issue.get("title", ""),
            url=issue.get("url", ""),
            status=state_info.get("name", "Unknown"),
            description=issue.get("description", ""),
        )
    except LinearAPIError as e:
        print(f"Error fetching ticket: {e}", file=sys.stderr)
        return None


async def get_project(project_id: str) -> LinearProject | None:
    """Get a Linear project by ID or name."""
    try:
        data = await _execute_query(GET_PROJECT_QUERY, {"id": project_id})
        project = data.get("project")

        if not project:
            print(f"Could not find project: {project_id}", file=sys.stderr)
            return None

        return LinearProject(
            id=project.get("id", ""),
            name=project.get("name", ""),
            url=project.get("url", ""),
            description=project.get("description", ""),
        )
    except LinearAPIError as e:
        print(f"Error fetching project: {e}", file=sys.stderr)
        return None


async def get_project_tickets(project_id: str) -> list[LinearTicket]:
    """Get all tickets for a Linear project."""
    tickets: list[LinearTicket] = []

    print(f"  Searching for project: {project_id}", file=sys.stderr)

    try:
        data = await _execute_query(LIST_PROJECT_ISSUES_QUERY, {"projectId": project_id})
        project = data.get("project")

        if project:
            issues = project.get("issues", {}).get("nodes", [])
            for issue in issues:
                state_info = issue.get("state", {})
                tickets.append(
                    LinearTicket(
                        id=issue.get("id", ""),
                        identifier=issue.get("identifier", ""),
                        title=issue.get("title", ""),
                        url=issue.get("url", ""),
                        status=state_info.get("name", "Unknown"),
                        description=issue.get("description", ""),
                    )
                )
        else:
            search_data = await _execute_query(SEARCH_PROJECTS_QUERY, {"query": project_id})
            projects = search_data.get("projects", {}).get("nodes", [])

            if projects:
                found_project = projects[0]
                found_id = found_project.get("id")
                print(
                    f"  Found project: {found_project.get('name')} ({found_id})", file=sys.stderr
                )

                issues_data = await _execute_query(
                    LIST_PROJECT_ISSUES_QUERY, {"projectId": found_id}
                )
                project_data = issues_data.get("project", {})
                issues = project_data.get("issues", {}).get("nodes", [])

                for issue in issues:
                    state_info = issue.get("state", {})
                    tickets.append(
                        LinearTicket(
                            id=issue.get("id", ""),
                            identifier=issue.get("identifier", ""),
                            title=issue.get("title", ""),
                            url=issue.get("url", ""),
                            status=state_info.get("name", "Unknown"),
                            description=issue.get("description", ""),
                        )
                    )

        if tickets:
            print(f"  Found {len(tickets)} tickets in project", file=sys.stderr)
        else:
            print(f"  No tickets found for project: {project_id}", file=sys.stderr)

    except LinearAPIError as e:
        print(f"  Error fetching project tickets: {e}", file=sys.stderr)

    return tickets


def to_dict(obj) -> dict:
    """Convert dataclass to dict for JSON output."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
    return {}


# CLI Commands
async def cmd_get_ticket(args):
    ticket = await get_ticket(args.ticket_id)
    if ticket:
        print(json.dumps(to_dict(ticket), indent=2))
    else:
        sys.exit(1)


async def cmd_create_ticket(args):
    ticket = await create_ticket(
        title=args.title,
        description=args.description or "",
        team=args.team,
        project_id=args.project,
        state=args.state,
    )
    if ticket.id:
        print(json.dumps(to_dict(ticket), indent=2))
    else:
        sys.exit(1)


async def cmd_update_status(args):
    success = await update_ticket_status(args.ticket_id, args.status)
    if success:
        print(json.dumps({"success": True, "ticket_id": args.ticket_id, "status": args.status}))
    else:
        sys.exit(1)


async def cmd_add_comment(args):
    success = await add_comment(args.ticket_id, args.body)
    if success:
        print(json.dumps({"success": True, "ticket_id": args.ticket_id}))
    else:
        sys.exit(1)


async def cmd_get_project(args):
    project = await get_project(args.project_id)
    if project:
        print(json.dumps(to_dict(project), indent=2))
    else:
        sys.exit(1)


async def cmd_get_project_tickets(args):
    tickets = await get_project_tickets(args.project_id)
    print(json.dumps([to_dict(t) for t in tickets], indent=2))


async def cmd_create_project(args):
    project = await create_project(
        name=args.name,
        description=args.description or "",
        team=args.team,
    )
    if project.id:
        print(json.dumps(to_dict(project), indent=2))
    else:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Linear CLI Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("get-ticket", help="Get ticket details")
    p.add_argument("ticket_id", help="Ticket ID or identifier (e.g., STAFF-123)")

    p = subparsers.add_parser("create-ticket", help="Create a new ticket")
    p.add_argument("--team", required=True, help="Team key (staff, defects, etc.)")
    p.add_argument("--title", required=True, help="Ticket title")
    p.add_argument("--description", help="Ticket description")
    p.add_argument("--project", help="Project ID to add ticket to")
    p.add_argument("--state", help="Initial state (Todo, In Progress, etc.)")

    p = subparsers.add_parser("update-status", help="Update ticket status")
    p.add_argument("ticket_id", help="Ticket ID or identifier")
    p.add_argument("--status", required=True, help="New status")

    p = subparsers.add_parser("add-comment", help="Add comment to ticket")
    p.add_argument("ticket_id", help="Ticket ID or identifier")
    p.add_argument("--body", required=True, help="Comment body (markdown)")

    p = subparsers.add_parser("get-project", help="Get project details")
    p.add_argument("project_id", help="Project ID or name")

    p = subparsers.add_parser("get-project-tickets", help="List project tickets")
    p.add_argument("project_id", help="Project ID or name")

    p = subparsers.add_parser("create-project", help="Create a new project")
    p.add_argument("--team", required=True, help="Team key")
    p.add_argument("--name", required=True, help="Project name")
    p.add_argument("--description", help="Project description")

    args = parser.parse_args()

    if args.command == "get-ticket":
        asyncio.run(cmd_get_ticket(args))
    elif args.command == "create-ticket":
        asyncio.run(cmd_create_ticket(args))
    elif args.command == "update-status":
        asyncio.run(cmd_update_status(args))
    elif args.command == "add-comment":
        asyncio.run(cmd_add_comment(args))
    elif args.command == "get-project":
        asyncio.run(cmd_get_project(args))
    elif args.command == "get-project-tickets":
        asyncio.run(cmd_get_project_tickets(args))
    elif args.command == "create-project":
        asyncio.run(cmd_create_project(args))


if __name__ == "__main__":
    main()
