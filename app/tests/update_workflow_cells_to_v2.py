"""Analyze and containerize notebook cells referenced by workflow fixtures."""

import argparse
import json
import os
import shlex
import shutil
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from slugify import slugify

RESOURCES = Path(__file__).resolve().parent / "resources"
ENV_FILE = Path(__file__).resolve().parents[2] / "dev-setup.env"
DEFAULT_URL = (
    "https://naavre-dev.minikube.test/"
    "naavre-containerizer-service/extract_cell"
)
SPECIAL_TYPES = {"splitter", "merger", "fdo-writer"}


def get_auth_token():
    token = os.environ.get("AUTH_TOKEN")
    if token:
        return token
    try:
        with ENV_FILE.open(encoding="utf-8") as file:
            for line in file:
                key, separator, value = line.strip().removeprefix(
                    "export ").partition("=")
                if separator and key.strip() == "AUTH_TOKEN":
                    parts = shlex.split(value, comments=True)
                    if len(parts) != 1:
                        raise ValueError("invalid AUTH_TOKEN in dev-setup.env")
                    return parts[0]
    except FileNotFoundError:
        return None
    return None


def notebook_titles(notebook):
    titles = {}
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        source = "".join(source) if isinstance(source, list) else source
        lines = source.splitlines()
        if not lines or not lines[0].lstrip().startswith("#"):
            continue
        title = slugify(lines[0].lstrip()[1:].strip())
        titles.setdefault(title, []).append(index)
    return titles


def analyze_folder(folder, *, url, token, virtual_lab=None, verify=True,
                   containerize_url=None):
    destination = folder.with_name(folder.name + "_v2")
    if destination.exists() or destination.is_symlink():
        print(f"{destination}: destination already exists;",
              file=sys.stderr)
        return False
    try:
        with (folder / "wf.naavrewf").open(encoding="utf-8") as f:
            workflow = json.load(f)
            nodes = workflow["chart"]["nodes"]
        with (folder / "notebook.ipynb").open(encoding="utf-8") as f:
            notebook = json.load(f)
        if virtual_lab is None:
            with (folder / "wf_payload.json").open(encoding="utf-8") as f:
                virtual_lab = json.load(f)["virtual_lab"]
        titles = notebook_titles(notebook)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"{folder}: failed to load fixtures: {exc}", file=sys.stderr)
        return False

    success = True
    updates = {}
    containerize_url = containerize_url or urljoin(url, "containerize")
    for node_id, node in nodes.items():
        try:
            cell = node["properties"]["cell"]
            if cell.get("type") in SPECIAL_TYPES:
                print(f"{folder.name}/{node_id}: skipping {cell['type']}")
                continue
            title = cell["title"].removesuffix("-user")
            matches = titles.get(title, [])
            if len(matches) != 1:
                raise ValueError(
                    f"expected one notebook cell for {title!r}, "
                    f"found {len(matches)}"
                )
            kernel = cell.get("kernel")
            if not kernel or not virtual_lab:
                raise ValueError(
                    "kernel, and virtual lab are required")
            payload = {
                "virtual_lab": virtual_lab,
                "data": {
                    "cell_index": matches[0],
                    "kernel": kernel,
                    "notebook": notebook
                },
            }
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
                json=payload, timeout=60, verify=verify,
            )
            response.raise_for_status()
            extracted_cell = response.json()
            if not isinstance(extracted_cell, dict):
                raise ValueError("extract_cell returned a non-object response")
            missing = [
                key for key in ("title", "base_container_image", "kernel",
                                "original_source")
                if key not in extracted_cell
            ]
            if missing:
                raise ValueError(
                    "extract_cell response is missing: " + ", ".join(missing)
                )
            response = requests.post(
                containerize_url,
                headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
                json={
                    "virtual_lab": virtual_lab,
                    "cell": extracted_cell,
                    "force_containerize": False,
                },
                timeout=60, verify=verify,
            )
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("containerize returned a non-object response")
            updates[node_id] = {
                "container_image": result["container_image"],
                "source_url": result["source_url"],
            }
            print(f"{folder.name}/{node_id} ({title}) containerized: "
                  f"{response.text}")
        except (KeyError, TypeError, ValueError,
                requests.RequestException) as exc:
            print(f"{folder.name}/{node_id}: {exc}", file=sys.stderr)
            success = False
    if updates:
        try:
            for node_id, fields in updates.items():
                nodes[node_id]["properties"]["cell"].update(fields)
            shutil.copytree(folder, destination)
            with ((destination / "wf.naavrewf").open("w", encoding="utf-8")
                  as f):
                json.dump(workflow, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"Updated workflow copy: {destination}")
        except OSError as exc:
            print(f"{destination}: failed to create workflow copy: {exc}",
                  file=sys.stderr)
            success = False
    return success


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "folder", nargs="?", type=Path, default=RESOURCES,
        help="A fixture folder or a directory containing fixture folders",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="extract_cell URL")
    parser.add_argument(
        "--containerize-url",
        help="Containerize URL (default: containerize beside --url)",
    )
    parser.add_argument(
        "--virtual-lab", default=os.environ.get("VIRTUAL_LAB") or "openlab",
        help="Virtual lab (default: VIRTUAL_LAB or openlab)",
    )
    tls = parser.add_mutually_exclusive_group()
    tls.add_argument(
        "--insecure", dest="verify", action="store_false",
        help="Disable TLS certificate verification (default)",
    )
    tls.add_argument(
        "--verify", dest="verify", action="store_true",
        help="Enable TLS certificate verification",
    )
    parser.set_defaults(verify=False)
    args = parser.parse_args(argv)
    try:
        token = get_auth_token()
    except (OSError, ValueError) as exc:
        parser.error(f"failed to read AUTH_TOKEN from dev-setup.env: {exc}")
    if not token:
        parser.error("set AUTH_TOKEN in the environment or dev-setup.env")
    if not args.folder.is_dir():
        parser.error(f"not a directory: {args.folder}")
    if (args.folder / "wf.naavrewf").is_file():
        folders = [args.folder]
    else:
        folders = sorted(p.parent for p in args.folder.glob("*/wf.naavrewf")
                         if not p.parent.name.endswith("_v2"))
    if not folders:
        parser.error(f"no workflow fixtures found in {args.folder}")
    success = True
    for folder in folders:
        if not analyze_folder(
                folder, url=args.url,
                token=token,
                virtual_lab=args.virtual_lab,
                verify=args.verify,
                containerize_url=args.containerize_url,
        ):
            success = False
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
