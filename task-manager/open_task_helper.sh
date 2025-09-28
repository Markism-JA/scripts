#!/bin/sh

FILE_PATH="$1"

# Use nohup to ensure the command runs completely detached from the GUI,
# preventing any race conditions or crashes.
# The 'sh -c' wrapper helps with complex command execution.
nohup sh -c '
  # Use a case statement to check the file extension.
  case "'"$FILE_PATH"'" in
    # If it is one of these text-based files...
    *.md|*.txt|*.py|*.sh|*.conf|*.json|*.yaml)
      # ...launch Kitty and tell it to run Neovim with the file.
      kitty nvim "'"$FILE_PATH"'"
      ;;
    # For all other files (PDFs, ZIPs, directories, etc.)...
    *)
      # ...use the standard xdg-open for graphical applications.
      xdg-open "'"$FILE_PATH"'"
      ;;
  esac
' >/dev/null 2>&1 &
