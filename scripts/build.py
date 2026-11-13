#!/usr/bin/env python3
"""Build the group directory and optionally analyze public repos with RepoSense."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DATA_FILE = "dashboard-data.json"
REPORT_DIR = "reposense-report"
GITHUB_REPOSITORY = re.compile(r"https://github\.com/([A-Za-z0-9-]+/[A-Za-z0-9_.-]+)/?")
# RepoSense tries to read this directory as a file in Group 06.
REPOSITORY_IGNORE_GLOBS = {
    "chengmeizeng9-ctrl/ceg5206-group6": ["results/full", "results/full/**"],
}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def repo_slug(url):
    match = GITHUB_REPOSITORY.fullmatch(url)
    if match is None:
        raise ValueError(f"Expected a GitHub repository URL (https://github.com/owner/repo): {url!r}")
    slug = match.group(1).removesuffix(".git")
    if slug.split("/")[1] in ("", ".", ".."):
        raise ValueError(f"Invalid GitHub repository name: {url!r}")
    return slug


def read_config():
    config = json.loads((ROOT / "groups.json").read_text(encoding="utf-8"))
    course = config["course"]
    if any(not isinstance(course[key], str) or not course[key].strip() for key in ("code", "title")):
        raise ValueError("Enter a course code and title in groups.json.")

    group_ids = set()
    for group in config["groups"]:
        group_id = group["id"]
        if not isinstance(group_id, str) or not re.fullmatch(r"[0-9]{2}", group_id) or group_id in group_ids:
            raise ValueError(f"Each group ID must be a unique two-digit string: {group_id!r}")
        group_ids.add(group_id)
        if group["url"] is not None:
            repo_slug(group["url"])

    config["groups"].sort(key=lambda group: group["id"])
    return config


def public_default_branch(url):
    """Return a default branch only when GitHub confirms public visibility."""
    request = Request(
        f"https://api.github.com/repos/{repo_slug(url)}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "CEG5206-Code-Dashboard"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            metadata = json.load(response)
    except HTTPError as error:
        if error.code in (404, 410, 451):
            print(f"Skipping {url}: unavailable to the public (HTTP {error.code}).", file=sys.stderr)
            return None
        raise RuntimeError(f"GitHub could not verify {url} (HTTP {error.code}).") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"GitHub could not verify {url}: {error}") from error

    if metadata.get("private") is not False or metadata.get("visibility") != "public":
        print(f"Skipping {url}: repository visibility is not public.", file=sys.stderr)
        return None
    branch = metadata.get("default_branch")
    if not isinstance(branch, str) or not branch:
        print(f"Skipping {url}: GitHub did not provide a default branch.", file=sys.stderr)
        return None
    return branch


def anonymous_git_environment():
    """Keep the public report build independent of local Git credentials."""
    env = {
        name: value for name, value in os.environ.items()
        if not name.startswith(("GIT_CONFIG_", "GIT_TRACE"))
           and name not in {"GIT_CONFIG", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"}
    }
    env.update({
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": os.devnull,
    })
    return env


def run_reposense(jar, work, output, course_code, repositories, since, until):
    config_dir = work / "config"
    config_dir.mkdir()
    # JSON is valid YAML. RepoSense reads its report title and group blurbs from this file.
    write_json(config_dir / "report-config.yaml", {
        "title": f"{course_code} Group Project Contributions",
        "repos": [
            {
                "repo": f"https://github.com/{repo_slug(repo['url'])}.git",
                "branches": [{
                    "branch": repo["branch"],
                    "blurb": f"Group {', '.join(repo['groups'])}",
                    "ignore-glob-list": REPOSITORY_IGNORE_GLOBS.get(
                        repo_slug(repo["url"]).lower(), []
                    ),
                }],
            }
            for repo in repositories
        ],
    })
    command = [
        "java", "--add-opens", "java.base/java.time=ALL-UNNAMED", "-jar", str(jar),
        "--config", str(config_dir), "--output", str(output), "--since", since,
        "--timezone", "Asia/Singapore", "--ignore-standalone-config",
    ]
    if until:
        command.extend(["--until", until])
    subprocess.run(command, cwd=work, env=anonymous_git_environment(), check=True, timeout=1200)

    report = output / REPORT_DIR
    if not (report / "index.html").is_file():
        raise RuntimeError("RepoSense did not produce a report. Check the RepoSense build log above.")
    shutil.rmtree(report / "reposense-logs", ignore_errors=True)
    summary = json.loads((report / "summary.json").read_text(encoding="utf-8"))
    included = set()
    for repo in summary["repos"]:
        data = report / repo["outputFolderName"]
        if (data / "commits.json").is_file() and (data / "authorship.json").is_file():
            included.add(repo_slug(repo["location"]["location"]).lower())
    if not included:
        raise RuntimeError("RepoSense did not produce data for any public repository. Check the build log above.")
    return included


def generate_report(jar, work, output, config, since, until):
    linked_groups = [group for group in config["groups"] if group["url"]]
    candidates = {}
    for group in linked_groups:
        slug = repo_slug(group["url"]).lower()
        if slug not in candidates:
            candidates[slug] = {"url": group["url"], "groups": []}
        candidates[slug]["groups"].append(group["id"])

    repositories = []
    for repo in candidates.values():
        branch = public_default_branch(repo["url"])
        if branch:
            repositories.append({**repo, "branch": branch})

    included = set()
    if repositories:
        included = run_reposense(jar, work, output, config["course"]["code"], repositories, since, until)
    groups = [group["id"] for group in linked_groups if repo_slug(group["url"]).lower() in included]
    unavailable = [group["id"] for group in linked_groups if group["id"] not in groups]
    if unavailable:
        print(f"Contribution report unavailable for groups {', '.join(unavailable)}.", file=sys.stderr)

    return {
        "available": bool(groups),
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds") if groups else None,
        "groups": groups,
        "unavailableGroups": unavailable,
    }


def check_output(output):
    if output.is_symlink():
        raise ValueError(f"Output must be a regular directory: {output}")
    if output.exists() and (
            not output.is_dir() or (any(output.iterdir()) and not (output / DATA_FILE).is_file())
    ):
        raise ValueError(f"Choose an empty output directory or an existing dashboard build: {output}")


def build(args):
    config = read_config()
    output = args.output.absolute()
    check_output(output)
    if args.jar and not args.jar.is_file():
        raise ValueError(f"RepoSense JAR not found: {args.jar}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dashboard-build-", dir=output.parent) as directory:
        work = Path(directory).resolve()
        staging = work / "site"
        shutil.copytree(SITE, staging)
        report = {"available": False, "generatedAt": None, "groups": [], "unavailableGroups": []}
        if args.jar:
            report = generate_report(args.jar.resolve(), work, staging, config, args.since, args.until)
        write_json(staging / DATA_FILE, {**config, "report": report})

        check_output(output)
        previous = work / "previous"
        if output.exists():
            output.rename(previous)
        try:
            staging.rename(output)
        except OSError:
            if previous.exists() and not output.exists():
                previous.rename(output)
            raise
    print(f"Built dashboard in {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="destination directory (default: dist)")
    parser.add_argument("--jar", type=Path, help="path to RepoSense.jar; omit for an offline directory build")
    parser.add_argument("--since", default="d1", help="first commit date, DD/MM/YYYY (default: first commit)")
    parser.add_argument("--until", help="last commit date, DD/MM/YYYY (default: today)")
    args = parser.parse_args()
    try:
        for date in (args.since, args.until):
            if date and date != "d1":
                datetime.strptime(date, "%d/%m/%Y")
        if args.until == "d1":
            raise ValueError("--until requires a date in DD/MM/YYYY format.")
        if args.since != "d1" and args.until and (
                datetime.strptime(args.since, "%d/%m/%Y") > datetime.strptime(args.until, "%d/%m/%Y")
        ):
            raise ValueError("--since must be on or before --until.")
        build(args)
    except (KeyError, TypeError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Dashboard build failed: {error}\n")


if __name__ == "__main__":
    main()
