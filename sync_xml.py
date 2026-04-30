import hashlib
import json
import os
import re
import subprocess


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "tei")
JSON_FILE = os.path.join(SCRIPT_DIR, "index.json")


def get_last_modified_datetime(file_path):
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.path.dirname(file_path),
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()

        relative_path = os.path.relpath(file_path, repo_root).replace("\\", "/")

        last_modified = subprocess.check_output(
            [
                "git",
                "log",
                "-1",
                "--format=%cd",
                "--date=format:%Y-%m-%d %H:%M:%S",
                "--",
                relative_path,
            ],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()

        if last_modified:
            return last_modified
    except Exception as exc:
        print(f"Git date error for {os.path.basename(file_path)}: {exc}")

    return "Unknown"


def read_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def strip_tags(value):
    return re.sub(r"<[^>]+>", "", value).strip()


def get_title_from_xml(file_path):
    try:
        content = read_file(file_path)
        match = re.search(
            r"<title[^>]+type=[\"']main[\"'][^>]*>(.*?)</title>",
            content,
            re.DOTALL,
        )
        if match:
            title = strip_tags(match.group(1))
            if title:
                return title
    except Exception as exc:
        print(f"Error reading title from {os.path.basename(file_path)}: {exc}")

    return "Unknown"


def get_author_from_xml(file_path):
    try:
        content = read_file(file_path)
        match = re.search(
            r"<author\b[^>]*>.*?<persName\b[^>]*>(.*?)</persName>.*?</author>",
            content,
            re.DOTALL,
        )
        if match:
            author = strip_tags(match.group(1))
            if author:
                return author
    except Exception as exc:
        print(f"Error reading author from {os.path.basename(file_path)}: {exc}")

    return "Unknown"


def get_publication_year(file_path):
    try:
        content = read_file(file_path)
        match = re.search(
            r"<bibl[^>]+type=[\"']originalSource[\"'][^>]*>.*?(\d{4}).*?</bibl>",
            content,
            re.DOTALL,
        )
        if match:
            return match.group(1)
    except Exception as exc:
        print(f"Error reading year from {os.path.basename(file_path)}: {exc}")

    return "Unknown"


def generate_id(filename):
    hash_object = hashlib.md5(filename.encode())
    return f"doc_{hash_object.hexdigest()[:8]}"


def load_existing_statuses():
    existing_status = {}

    if not os.path.exists(JSON_FILE):
        return existing_status

    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            old_data = json.load(file)

        for item in old_data:
            storage_path = item.get("storage_path", "")
            file_name = os.path.basename(storage_path) if storage_path else item.get("title", "")
            existing_status[file_name] = item.get("status", "drafts")
    except Exception as exc:
        print(f"Could not read existing JSON ({exc}), creating fresh.")

    return existing_status


def update_manifest():
    print(f"Looking for data in: {BASE_DIR}")
    print("Start updating database...")

    if not os.path.exists(BASE_DIR):
        print(f"Error: folder not found: {BASE_DIR}")
        return

    existing_status = load_existing_statuses()
    new_list = []
    files = sorted(file_name for file_name in os.listdir(BASE_DIR) if file_name.endswith(".xml"))

    for file_name in files:
        full_path = os.path.join(BASE_DIR, file_name)
        relative_path = os.path.relpath(full_path, SCRIPT_DIR).replace("\\", "/")

        new_list.append(
            {
                "id": generate_id(file_name),
                "title": get_title_from_xml(full_path),
                "author": get_author_from_xml(full_path),
                "year": get_publication_year(full_path),
                "status": existing_status.get(file_name, "drafts"),
                "last_modified": get_last_modified_datetime(full_path),
                "storage_path": relative_path,
            }
        )

    new_list.sort(key=lambda item: item["title"])

    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(new_list, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print("Success! Database updated.")
    print(f"Total documents: {len(new_list)}")


if __name__ == "__main__":
    update_manifest()
