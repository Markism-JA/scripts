#!/usr/bin/env python3

"""
check_tasks: A CLI tool to manage and prioritize academic tasks from any file type
using a CENTRALIZED metadata file.

WARNING: Renaming or moving task files outside of this script will break the link
to their metadata.
"""

import os
import sys
import subprocess
import yaml
from pathlib import Path
import argparse
from datetime import date, datetime

SCHOOL_FILES_DIR = Path(os.path.expanduser("~/Documents/School-Files"))
DASHBOARD_DIR = Path(os.path.expanduser("~/Downloads/Ongoing"))
ONGOING_DIR_NAME = "ongoing"
COMPLETED_DIR_NAME = "completed"
METADATA_FILE = DASHBOARD_DIR / "metadata.yaml"


def load_metadata():
    """Loads the central metadata file."""
    if not METADATA_FILE.exists():
        return {}
    with open(METADATA_FILE, "r") as f:
        return yaml.safe_load(f) or {}


def save_metadata(data):
    """Saves data to the central metadata file."""
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        yaml.dump(data, f, indent=2)


def get_subjects():
    """Returns a list of all subject directories."""
    if not SCHOOL_FILES_DIR.is_dir():
        print(f"Error: School files directory not found at '{SCHOOL_FILES_DIR}'")
        sys.exit(1)
    return [d for d in SCHOOL_FILES_DIR.iterdir() if d.is_dir()]


def calculate_urgency(due_date_obj):
    if due_date_obj is None:
        return 0
    days_remaining = (due_date_obj - date.today()).days
    if days_remaining <= 2:
        return 5
    elif days_remaining <= 7:
        return 4
    elif days_remaining <= 14:
        return 3
    elif days_remaining <= 30:
        return 2
    else:
        return 1


def calculate_priority(due_date_obj, difficulty):
    return (calculate_urgency(due_date_obj) * 2) + difficulty


def handle_init():
    """Initializes the required directory structure."""
    print("Initializing directories...")
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured dashboard directory exists: '{DASHBOARD_DIR}'")
    if not METADATA_FILE.exists():
        save_metadata({})
        print(f"Created central metadata file: '{METADATA_FILE}'")

    for subject_path in get_subjects():
        (subject_path / ONGOING_DIR_NAME).mkdir(exist_ok=True)
        (subject_path / COMPLETED_DIR_NAME).mkdir(exist_ok=True)
        print(f"  - Ensured 'ongoing' and 'completed' exist for '{subject_path.name}'")
    print("\nInitialization complete.")


def get_all_rated_tasks():
    """Reads the central metadata file and returns a list of task dicts."""
    metadata = load_metadata()
    tasks = []
    for rel_path_str, data in metadata.items():
        try:
            full_path = SCHOOL_FILES_DIR / rel_path_str
            if not full_path.exists():
                print(
                    f"Warning: Task '{rel_path_str}' not found on disk. It will be ignored."
                )
                continue

            due_date_str = data.get("due_date")
            due_date_obj = (
                datetime.strptime(due_date_str, "%Y-%m-%d").date()
                if due_date_str
                else None
            )
            difficulty = data.get("difficulty", 1)

            priority = calculate_priority(due_date_obj, difficulty)

            tasks.append(
                {
                    "path": full_path,
                    "rel_path": rel_path_str,
                    "subject": full_path.parent.parent.name,
                    "priority": priority,
                    "difficulty": difficulty,
                    "due_date": due_date_obj,
                }
            )
        except (KeyError, ValueError) as e:
            print(f"Warning: Could not process metadata for '{rel_path_str}': {e}")
    return tasks


def handle_refresh():
    """Clears and rebuilds the dashboard with prioritized symlinks."""
    print("Refreshing dashboard...")
    if not DASHBOARD_DIR.is_dir():
        print(f"Dashboard directory '{DASHBOARD_DIR}' not found. Run --init first.")
        return

    for item in DASHBOARD_DIR.iterdir():
        if item.is_symlink():
            item.unlink()

    tasks = get_all_rated_tasks()
    sorted_tasks = sorted(tasks, key=lambda x: x["priority"], reverse=True)

    if not sorted_tasks:
        print("No rated tasks found to display.")
        return

    for i, task in enumerate(sorted_tasks, 1):
        clean_name = task["path"].name.replace(" ", "-")
        clean_subject_name = task["subject"].replace(" ", "-")
        link_name = f"{i:02d}-{clean_subject_name}-{clean_name}"
        link_path = DASHBOARD_DIR / link_name
        try:
            os.symlink(task["path"], link_path)
        except OSError as e:
            print(f"Error creating symlink: {e}")

    print(f"Dashboard refreshed with {len(sorted_tasks)} tasks.")


def get_date_input(prompt, current=None):
    """Prompts user for a date and validates the format."""
    while True:
        date_str = input(prompt).strip()
        if not date_str:
            return current
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(
                "  Invalid format. Please use YYYY-MM-DD or press Enter to keep current value."
            )


def get_validated_input(prompt, current=None, min_val=1, max_val=5):
    """Prompts user for an integer and validates it."""
    while True:
        value_str = input(prompt).strip()
        if not value_str:
            return current
        try:
            value = int(value_str)
            if min_val <= value <= max_val:
                return value
            else:
                print(f"  Please enter a number between {min_val} and {max_val}.")
        except ValueError:
            print("  Invalid input. Please enter a number.")


def handle_check():
    """Scans for new, unrated items and adds them to the central metadata file."""
    print("Checking for new tasks...")
    metadata = load_metadata()
    new_tasks = []

    for subject_path in get_subjects():
        ongoing_path = subject_path / ONGOING_DIR_NAME
        if not ongoing_path.is_dir():
            continue

        for item_path in ongoing_path.iterdir():
            if item_path.name.startswith("."):
                continue

            rel_path = item_path.relative_to(SCHOOL_FILES_DIR)
            if str(rel_path) not in metadata:
                new_tasks.append(
                    {
                        "path": item_path,
                        "rel_path": str(rel_path),
                        "subject": subject_path.name,
                    }
                )

    if not new_tasks:
        print("No new tasks to review.")
        return

    print(f"Found {len(new_tasks)} new task(s).\n")
    for task in new_tasks:
        item_path = task["path"]
        print(f"New Task: [{task['subject']}] {item_path.name}")

        open_choice = input("Open to review? [y/N]: ").lower().strip()
        if open_choice == "y":
            try:
                subprocess.run(["xdg-open", str(item_path)])
            except Exception as e:
                print(f"Error: Could not open file '{item_path}'. {e}")

        due_date_obj = get_date_input(
            "Enter Due Date (YYYY-MM-DD) or press Enter for none: "
        )
        difficulty = get_validated_input(
            "Enter difficulty (1-5, 5 is most difficult): "
        )

        metadata[task["rel_path"]] = {
            "due_date": due_date_obj.strftime("%Y-%m-%d") if due_date_obj else None,
            "difficulty": difficulty,
        }
        print(f"  -> Added metadata for '{item_path.name}'.\n")

    save_metadata(metadata)
    print("All new tasks have been rated. Refreshing dashboard...")
    handle_refresh()


def handle_complete():
    """Moves completed tasks and removes their metadata entries."""
    tasks = get_all_rated_tasks()
    sorted_tasks = sorted(tasks, key=lambda x: x["priority"], reverse=True)
    if not sorted_tasks:
        print("No tasks to complete.")
        return

    print("Current tasks:")
    for i, task in enumerate(sorted_tasks, 1):
        due_date_str = (
            task["due_date"].strftime("%Y-%m-%d") if task["due_date"] else "N/A"
        )
        print(
            f"  {i:02d}: [{task['subject']}] {task['path'].name} (Due: {due_date_str}, Diff: {task['difficulty']})"
        )

    tasks_to_complete = []
    while True:
        choice_str = input(
            "\nEnter number(s) of tasks to complete (e.g., '1 4 5'), or 'q' to quit: "
        ).strip()
        if choice_str.lower() == "q":
            return

        choices = choice_str.split()
        if not choices:
            continue

        selected_indices = []
        valid_input = True
        for choice in choices:
            try:
                index = int(choice) - 1
                if 0 <= index < len(sorted_tasks):
                    selected_indices.append(index)
                else:
                    print(f"Error: Task number '{choice}' is out of range.")
                    valid_input = False
                    break
            except ValueError:
                print(f"Error: '{choice}' is not a valid number.")
                valid_input = False
                break

        if valid_input:
            tasks_to_complete = [sorted_tasks[i] for i in selected_indices]
            break

    if not tasks_to_complete:
        print("No valid tasks selected.")
        return

    metadata = load_metadata()
    for task in tasks_to_complete:
        item_path = task["path"]
        completed_path = item_path.parent.parent / COMPLETED_DIR_NAME
        try:
            item_path.rename(completed_path / item_path.name)
            print(f"Moved '{item_path.name}' to completed tasks.")

            if task["rel_path"] in metadata:
                del metadata[task["rel_path"]]
                print(f"  - Removed '{item_path.name}' from metadata.")

        except IOError as e:
            print(f"Error moving file '{item_path.name}': {e}")
            continue

    save_metadata(metadata)
    print("\nUpdating dashboard...")
    handle_refresh()


def handle_modify():
    """Allows modification of an existing task's due date and difficulty."""
    tasks = get_all_rated_tasks()
    sorted_tasks = sorted(tasks, key=lambda x: x["priority"], reverse=True)
    if not sorted_tasks:
        print("No tasks to modify.")
        return

    print("Current tasks:")
    for i, task in enumerate(sorted_tasks, 1):
        due_date_str = (
            task["due_date"].strftime("%Y-%m-%d") if task["due_date"] else "N/A"
        )
        print(
            f"  {i:02d}: [{task['subject']}] {task['path'].name} (Due: {due_date_str}, Diff: {task['difficulty']})"
        )

    while True:
        choice = input(
            "\nEnter the number of the task to modify (or 'q' to quit): "
        ).strip()
        if choice.lower() == "q":
            return
        try:
            task_to_modify = sorted_tasks[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print("Invalid number. Please try again.")

    print(f"\nModifying task: {task_to_modify['path'].name}")

    current_due_date = task_to_modify["due_date"]
    current_difficulty = task_to_modify["difficulty"]

    due_date_prompt = f"Enter new Due Date (YYYY-MM-DD) [current: {current_due_date.strftime('%Y-%m-%d') if current_due_date else 'None'}]: "
    new_due_date = get_date_input(due_date_prompt, current=current_due_date)

    difficulty_prompt = f"Enter new difficulty (1-5) [current: {current_difficulty}]: "
    new_difficulty = get_validated_input(difficulty_prompt, current=current_difficulty)

    metadata = load_metadata()
    if task_to_modify["rel_path"] in metadata:
        metadata[task_to_modify["rel_path"]]["due_date"] = (
            new_due_date.strftime("%Y-%m-%d") if new_due_date else None
        )
        metadata[task_to_modify["rel_path"]]["difficulty"] = new_difficulty
        save_metadata(metadata)
        print("\nTask metadata updated successfully.")
    else:
        print("Error: Could not find task in metadata to update.")
        return

    handle_refresh()


def modify_task_data(rel_path, new_due_date, new_difficulty):
    """Programmatically modifies the metadata for a single task."""
    metadata = load_metadata()
    if rel_path in metadata:
        metadata[rel_path]["due_date"] = new_due_date
        metadata[rel_path]["difficulty"] = new_difficulty
        save_metadata(metadata)
        print(f"Programmatically updated metadata for '{rel_path}'.")
        return True
    else:
        print(f"Error: Could not find task with rel_path '{rel_path}' in metadata.")
        return False


def get_all_tasks_with_details():
    """Gets all rated tasks and enriches them with full details for the GUI."""
    tasks = get_all_rated_tasks()
    sorted_tasks = sorted(tasks, key=lambda x: x["priority"], reverse=True)
    detailed_tasks = []
    for task in sorted_tasks:
        detailed_tasks.append(
            {
                "priority": task["priority"],
                "difficulty": task["difficulty"],
                "due_date": task["due_date"].strftime("%Y-%m-%d")
                if task["due_date"]
                else "N/A",
                "subject": task["subject"],
                "name": task["path"].name,
                "full_path": str(task["path"]),
                "rel_path": task["rel_path"],
            }
        )
    return detailed_tasks


def handle_export():
    """Exports all rated tasks as Tab-Separated Values (TSV)."""
    tasks = get_all_rated_tasks()
    sorted_tasks = sorted(tasks, key=lambda x: x["priority"], reverse=True)

    print("Priority\tDifficulty\tDue Date\tSubject\tName\tFull Path")

    for task in sorted_tasks:
        difficulty = task.get("difficulty", "N/A")
        due_date_obj = task.get("due_date")
        due_date = due_date_obj.strftime("%Y-%m-%d") if due_date_obj else "N/A"

        print(
            f"{task['priority']}\t"
            f"{difficulty}\t"
            f"{due_date}\t"
            f"{task['subject']}\t"
            f"{task['path'].name}\t"
            f"{task['path']}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="A CLI tool to manage academic tasks with a central metadata file."
    )
    parser.add_argument(
        "--init", action="store_true", help="Initialize the directory structure."
    )
    parser.add_argument(
        "-c", "--check", action="store_true", help="Check for and rate new tasks."
    )
    parser.add_argument(
        "-r", "--refresh", action="store_true", help="Refresh the dashboard."
    )
    parser.add_argument(
        "--complete",
        "--done",
        action="store_true",
        help="Mark one or more tasks as complete.",
    )
    parser.add_argument(
        "-m",
        "--modify",
        action="store_true",
        help="Modify the data of an existing task.",
    )
    parser.add_argument(
        "--export", action="store_true", help="Export all task data in TSV format."
    )

    parser.set_defaults(func=handle_check)

    args = parser.parse_args()

    action_map = {
        "init": handle_init,
        "refresh": handle_refresh,
        "complete": handle_complete,
        "modify": handle_modify,
        "export": handle_export,
        "check": handle_check,
    }

    action_to_run = handle_check
    for action, func in action_map.items():
        if getattr(args, action, False):
            action_to_run = func
            break

    try:
        action_to_run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
