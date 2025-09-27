#!/usr/bin/env python3

import os
import sys
import subprocess
import json
import atexit
import shutil

# --- Configuration & State ---
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "rclone-tui-py")
PRESET_FILE = os.path.join(CONFIG_DIR, "presets.json")
MOUNTED_BY_SCRIPT = set()


# --- UI Helper Functions ---
def print_header(title):
    """Prints a styled header."""
    print("\n" + "=" * 50)
    print(f"### {title} ###")
    print("=" * 50)


def print_error(message):
    """Prints an error message."""
    print(f"\n[ERROR] {message}", file=sys.stderr)


def get_menu_choice(options, prompt="Select an option"):
    """Displays a menu and gets a valid user choice."""
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")

    while True:
        try:
            choice = int(input(f"{prompt} [1-{len(options)}]: "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Please enter a number.")


# --- Core Helper & Utility Functions ---


def check_dependencies():
    """Checks if rclone is installed."""
    if not shutil.which("rclone"):
        print_error("Required tool 'rclone' is not installed.")
        sys.exit(1)


def setup_env():
    """Creates the config directory and preset file if they don't exist."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(PRESET_FILE):
        with open(PRESET_FILE, "w") as f:
            json.dump({}, f)


def load_presets():
    """Loads presets from the JSON file."""
    try:
        with open(PRESET_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_presets(presets):
    """Saves presets to the JSON file."""
    with open(PRESET_FILE, "w") as f:
        json.dump(presets, f, indent=4)


# --- MODIFIED FUNCTION ---
def get_mount_point(remote_name):
    """Generates a sanitized mount point path in the user's home directory."""
    base_mount_dir = os.path.join(os.path.expanduser("~"), "rclone-mounts")
    sanitized = remote_name.lower().replace("_", "").replace("-", "").replace(":", "")
    return os.path.join(base_mount_dir, sanitized)


def is_mounted(mount_point):
    """Checks if a path is a currently mounted filesystem."""
    try:
        # os.path.ismount() can be unreliable for FUSE, so we parse 'mount' output
        result = subprocess.run(["mount"], capture_output=True, text=True, check=True)
        return f" on {os.path.realpath(mount_point)} " in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# --- Rclone Interaction Logic ---


def run_command(command, title=""):
    """
    Runs a shell command, streaming its output.
    This function expects 'command' to be a list of strings.
    """
    print_header(title)
    try:
        cmd_list = [str(item) for item in command]
        process = subprocess.Popen(
            cmd_list, stdout=sys.stdout, stderr=sys.stderr, text=True
        )
        process.communicate()
        print("--- End ---")
        return process.returncode
    except FileNotFoundError:
        print_error(f"Command not found: {command[0]}")
        return -1
    except Exception as e:
        print_error(f"Failed to execute command '{' '.join(command)}'.")
        print_error(f"Underlying error: {e}")
        return -1


def get_rclone_config_path():
    """
    Finds the rclone config file path by parsing the output of 'rclone config file'.
    """
    try:
        result = subprocess.run(
            ["rclone", "config", "file"], capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().splitlines()
        path = lines[-1].strip() if lines else ""
        if not os.path.exists(path):
            print_error(
                f"Failed to parse rclone config path.\nRaw output was: '{result.stdout.strip()}'\nParsed path was: '{path}'"
            )
            return None
        return path
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error(
            "Could not determine rclone config file location. Is rclone installed?"
        )
        return None


def get_rclone_remotes():
    """Gets a list of configured rclone remotes using the correct config file."""
    config_path = get_rclone_config_path()
    if not config_path:
        return []
    try:
        result = subprocess.run(
            ["rclone", "listremotes", "--config", config_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return [
            line.strip().replace(":", "") for line in result.stdout.splitlines() if line
        ]
    except subprocess.CalledProcessError as e:
        print_error(f"`rclone listremotes` failed!\nStderr: {e.stderr}")
        return []


# --- MODIFIED FUNCTION ---
def mount_remote(remote_name, interactive=True):
    """
    Handles the full mounting process for a remote.
    Can be run non-interactively for batch jobs.
    """
    mount_point = get_mount_point(remote_name)
    if is_mounted(mount_point):
        if interactive:
            print(f"\nInfo: '{remote_name}' is already mounted at '{mount_point}'.")
        return True

    # Only ask for confirmation if in interactive mode
    if interactive:
        if input(f"\nMount '{remote_name}'? [y/N]: ").lower() != "y":
            return False

    rclone_config_path = get_rclone_config_path()
    if not rclone_config_path:
        print_error(
            "Cannot mount remote because rclone config path could not be determined."
        )
        return False

    print(f"Creating mount point directory: {mount_point}")
    # Since this is in the user's home directory, no sudo is needed.
    try:
        os.makedirs(mount_point, exist_ok=True)
    except OSError as e:
        print_error(f"Failed to create mount point directory: {e}")
        return False

    mount_cmd = [
        "rclone",
        "mount",
        f"{remote_name}:",
        mount_point,
        "--config",
        rclone_config_path,
        "--vfs-cache-mode",
        "writes",
        "--daemon",
    ]
    title = (
        f"Mounting {remote_name}"
        if interactive
        else f"Mounting {remote_name} for batch job"
    )
    return_code = run_command(mount_cmd, title=title)

    if return_code == 0:
        print("\nSuccessfully mounted.")
        MOUNTED_BY_SCRIPT.add(mount_point)
        return True
    else:
        print_error(f"Mount command failed for {remote_name}.")
        # Attempt to clean up the created directory if mount fails
        try:
            os.rmdir(mount_point)
        except OSError:
            # Silently fail if rmdir doesn't work (e.g., not empty or no permissions)
            pass
        return False


# --- (create_preset_wizard and delete_preset_wizard are unchanged) ---
def create_preset_wizard(remote_name):
    """Interactive wizard to create a new preset."""
    print_header("Create New Preset Wizard")
    all_presets = load_presets()
    while True:
        preset_name = input("Enter a short, memorable name for this preset: ").strip()
        if not preset_name:
            print("Name cannot be empty.")
        elif preset_name in all_presets:
            print(f"Preset '{preset_name}' already exists. Please choose another name.")
        else:
            break
    while True:
        local_path = input(
            "Enter the full local path to sync (e.g., ~/Documents): "
        ).strip()
        expanded_path = os.path.expanduser(local_path)
        if not os.path.isdir(expanded_path):
            print(f"Path not found: '{expanded_path}'. Please enter a valid directory.")
        else:
            local_path = expanded_path
            break
    remote_path = input(
        f"Enter the remote sub-folder on '{remote_name}' (e.g., Backups/Work): "
    ).strip()
    print("\nEnter folders or patterns to ignore, separated by commas.")
    print(
        "Hint: End folders with a '/' (e.g., node_modules/, .git/). Wildcards are supported (*.log)."
    )
    ignore_input = input("Ignores (optional): ").strip()
    ignore_list = [item.strip() for item in ignore_input.split(",") if item.strip()]
    print("\n--- Confirm New Preset ---")
    print(f"  Name:   {preset_name}")
    print(f"  Local:  {local_path}")
    print(f"  Remote: {remote_name}:{remote_path}")
    if ignore_list:
        print(f"  Ignores: {ignore_list}")
    if input("Save this preset? [Y/n]: ").lower() != "n":
        new_preset = {
            "local_path": local_path,
            "remote_name": remote_name,
            "remote_path": remote_path,
            "ignores": ignore_list,
        }
        all_presets[preset_name] = new_preset
        save_presets(all_presets)
        print("\nPreset saved successfully!")
        return preset_name, new_preset
    else:
        print("\nPreset creation cancelled.")
        return None, None


def delete_preset_wizard():
    """Interactive wizard to delete an existing preset."""
    print_header("Delete Preset")
    all_presets = load_presets()
    if not all_presets:
        print("There are no presets to delete.")
        return
    preset_to_delete = get_menu_choice(
        list(all_presets.keys()), "Choose a preset to delete"
    )
    if (
        input(
            f"Are you sure you want to permanently delete '{preset_to_delete}'? [y/N]: "
        ).lower()
        == "y"
    ):
        del all_presets[preset_to_delete]
        save_presets(all_presets)
        print(f"Preset '{preset_to_delete}' has been deleted.")
    else:
        print("Deletion cancelled.")


# --- NEW FUNCTION ---
def sync_all_presets():
    """
    Sequentially syncs all defined presets from local to remote.
    """
    print_header("Sync All Presets")
    all_presets = load_presets()
    if not all_presets:
        print("No presets found to sync.")
        return

    # 1. Mount Manager: Find unique remotes and mount them all non-interactively.
    print("--- Phase 1: Mounting all required remotes ---")
    required_remotes = {details["remote_name"] for details in all_presets.values()}

    for remote in required_remotes:
        if not mount_remote(remote, interactive=False):
            print_error(
                f"Failed to mount required remote '{remote}'. Aborting Sync All."
            )
            return

    # 2. Execution Loop: Run sync for each preset.
    print("\n--- Phase 2: Syncing all presets sequentially ---")
    preset_count = len(all_presets)
    for i, (preset_name, preset_details) in enumerate(all_presets.items(), 1):
        print_header(f"Running Preset {i}/{preset_count}: '{preset_name}'")

        local_path = preset_details["local_path"]
        remote_name = preset_details["remote_name"]
        remote_path_segment = preset_details["remote_path"]
        mount_point = get_mount_point(remote_name)
        full_remote_path = os.path.join(mount_point, remote_path_segment)

        if not os.path.exists(local_path):
            print_error(f"Skipping preset: Local path does not exist: {local_path}")
            continue

        if not is_mounted(mount_point):
            print_error(
                f"Skipping preset: Required remote '{remote_name}' is not mounted."
            )
            continue

        base_cmd = ["rclone", "-P"]
        ignore_list = preset_details.get("ignores", [])
        if ignore_list:
            print(f"Applying ignore filters: {ignore_list}")
            for pattern in ignore_list:
                base_cmd.extend(["--filter", f"- {pattern}"])

        # For "Sync All", we assume Local -> Remote sync.
        final_cmd = base_cmd + ["sync", local_path, full_remote_path]
        run_command(final_cmd, f"Syncing '{preset_name}' (Local -> Remote)")

    print_header("Sync All Presets Complete")


# --- MODIFIED FUNCTION ---
def cleanup_on_exit():
    """Unmounts any remotes that were mounted by this session."""
    if not MOUNTED_BY_SCRIPT:
        return
    print("\nCleaning up mounted filesystems...")
    for mount_point in MOUNTED_BY_SCRIPT:
        print(f"Unmounting {mount_point}...")
        subprocess.run(["fusermount", "-u", mount_point], stderr=subprocess.DEVNULL)
        print(f"Removing directory {mount_point}...")
        # Sudo is not needed as the directory is in the user's home.
        subprocess.run(["rmdir", mount_point], stderr=subprocess.DEVNULL)
    print("Cleanup complete. Goodbye!")


# --- MODIFIED FUNCTION ---
def main_loop():
    """The main interactive loop for the application."""
    while True:
        print_header("Rclone TUI - Main Menu")
        main_choice = get_menu_choice(
            [
                "Manage/Run Individual Preset",
                "Sync All Presets (Local -> Remote)",
                "Delete a Preset",
                "Quit",
            ]
        )

        if main_choice == "Manage/Run Individual Preset":
            manage_and_run_presets()
        elif main_choice == "Sync All Presets (Local -> Remote)":
            sync_all_presets()
        elif main_choice == "Delete a Preset":
            delete_preset_wizard()
        elif main_choice == "Quit":
            sys.exit(0)


# --- (manage_and_run_presets and run_action_for_preset are unchanged) ---
def manage_and_run_presets():
    """Handles the workflow for selecting a remote and running a preset."""
    remotes = get_rclone_remotes()
    if not remotes:
        print_error("No rclone remotes found. Please configure rclone first.")
        return
    print_header("Select a Remote")
    selected_remote = get_menu_choice(remotes)
    # This will call mount_remote in interactive mode by default
    if not mount_remote(selected_remote):
        print_error("Could not mount remote. Returning to main menu.")
        return
    while True:
        all_presets = load_presets()
        remote_presets = {
            name: paths
            for name, paths in all_presets.items()
            if paths["remote_name"] == selected_remote
        }
        preset_names = list(remote_presets.keys())
        menu_options = preset_names + [
            "[+] Create a new preset for this remote",
            "[<] Back to Main Menu",
        ]
        print_header(f"Presets for {selected_remote}")
        choice = get_menu_choice(menu_options)
        if choice == "[<] Back to Main Menu":
            return
        elif choice == "[+] Create a new preset for this remote":
            selected_preset_name, preset_details = create_preset_wizard(selected_remote)
            if not selected_preset_name:
                continue
        else:
            selected_preset_name = choice
            preset_details = remote_presets[selected_preset_name]
        run_action_for_preset(selected_preset_name, preset_details)


def run_action_for_preset(preset_name, preset_details):
    """Shows the action menu and executes the choice with dynamic ignore filters."""
    local_path = preset_details["local_path"]
    remote_path_segment = preset_details["remote_path"]
    mount_point = get_mount_point(preset_details["remote_name"])
    full_remote_path = os.path.join(mount_point, remote_path_segment)
    print_header(f"Actions for '{preset_name}'")
    if not os.path.exists(local_path):
        print_error(f"The local path for this preset does not exist: {local_path}")
        return
    base_cmd = ["rclone", "-P"]
    ignore_list = preset_details.get("ignores", [])
    if ignore_list:
        print(f"Applying ignore filters: {ignore_list}")
        for pattern in ignore_list:
            base_cmd.extend(["--filter", f"- {pattern}"])
    action_choice = get_menu_choice(
        [
            "Sync (Local -> Remote)",
            "Reverse Sync (Remote -> Local)",
            "Check (Compares hashes)",
            "[<] Back to Preset List",
        ]
    )
    if action_choice == "Sync (Local -> Remote)":
        final_cmd = base_cmd + ["sync", local_path, full_remote_path]
        run_command(final_cmd, f"Syncing '{preset_name}' to Remote")
    elif action_choice == "Reverse Sync (Remote -> Local)":
        final_cmd = base_cmd + ["sync", full_remote_path, local_path]
        run_command(final_cmd, f"Syncing '{preset_name}' from Remote")
    elif action_choice == "Check (Compares hashes)":
        final_cmd = base_cmd + ["check", local_path, full_remote_path]
        run_command(final_cmd, f"Checking '{preset_name}'")
    elif action_choice == "[<] Back to Preset List":
        return


if __name__ == "__main__":
    try:
        print("Registering cleanup task...")
        atexit.register(cleanup_on_exit)
        check_dependencies()
        setup_env()
        main_loop()
    except KeyboardInterrupt:
        print("\n\nExiting on user request.")
        sys.exit(0)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
