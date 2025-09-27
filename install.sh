#!/bin/bash

# Installation script for the Simplified Pinned Items Rofi configuration
# Run this script to set up the enhanced Rofi configuration

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Rofi with Pinned Items...${NC}"

# Check if rofi is installed
if ! command -v rofi &>/dev/null; then
    echo -e "${RED}Rofi is not installed. Please install it first.${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p ~/.config/rofi/scripts

# Create config directory if it doesn't exist
echo -e "${BLUE}Creating Rofi configuration...${NC}"
mkdir -p ~/.config/rofi

# Check if master-config.rasi exists, create if not
if [ ! -f ~/.config/rofi/master-config.rasi ]; then
    echo -e "${BLUE}Creating master configuration file...${NC}"
    cat >~/.config/rofi/master-config.rasi <<EOL
/* Master configuration file for Rofi */
EOL
fi

# Install the enhanced theme
echo -e "${BLUE}Installing enhanced theme...${NC}"
cat >~/.config/rofi/config.rasi <<'EOL'
/* Material Design Dark Theme for Rofi with Pinned Items - 1080p */
@import "~/.config/rofi/master-config.rasi" 

/* ---- Configuration ---- */
configuration {
    font: "SpaceMonoNF 11";
    show-icons: true;
    display-drun: "";
    drun-display-format: "{name}";
    disable-history: false;
    sidebar-mode: true;
    modi: "drun,run,window,filebrowser,pinned:~/.config/rofi/scripts/pinned.sh";
}

/* ---- Color Variables ---- */
* {
    /* Material Dark Palette */
    background:         #121212;
    background-alt:     #1E1E1E;
    background-light:   #272727;
    foreground:         #FFFFFF;
    foreground-alt:     #EEEEEE;
    primary:            #BB86FC;
    primary-dark:       #9967D6;
    secondary:          #03DAC6;
    selected:           #BB86FC;
    urgent:             #CF6679;
    border:             #1F1F1F;
    separator:          #383838;
    placeholder:        #666666;
}

/* ---- Window ---- */
window {
    width: 60%;
    background-color: @background;
    border: 1px;
    border-color: @border;
    border-radius: 20px;
    padding: 0px;
    spacing: 0;
    transparency: "real";
}

/* ---- Mainbox ---- */
mainbox {
    background-color: transparent;
    children: [inputbar, separator, listview, separator, pinned-bar];
    spacing: 0;
    padding: 0;
    border-radius: 12px;
}

/* ---- Separator ---- */
separator {
    background-color: @separator;
    height: 1px;
}

/* ---- Inputbar ---- */
inputbar {
    background-color: @background-alt;
    children: [prompt, entry, mode-switcher];
    padding: 16px;
    spacing: 12px;
    border-radius: 12px 12px 0 0;
}

prompt {
    background-color: transparent;
    text-color: @primary;
    font: "Roboto Bold 12";
}

entry {
    background-color: transparent;
    text-color: @foreground;
    placeholder: "Type to search...";
    placeholder-color: @placeholder;
    padding: 0 0 0 4px;
    expand: true;
}

/* ---- Mode Switcher ---- */
mode-switcher {
    background-color: transparent;
    orientation: horizontal;
    spacing: 8px;
}

button {
    padding: 4px 12px;
    background-color: @background-light;
    text-color: @foreground;
    border-radius: 12px;
    horizontal-align: 0.5;
}

button selected {
    background-color: @primary;
    text-color: @background;
    border-radius: 12px;
}

/* ---- Listview ---- */
listview {
    background-color: @background;
    columns: 6;
    lines: 4;
    fixed-height: true;
    spacing: 12px;
    padding: 16px;
    scrollbar: true;
    border: 0;
    dynamic: true;
    cycle: false;
}

scrollbar {
    width: 4px;
    border: 0;
    handle-width: 8px;
    padding: 0;
    handle-color: @primary;
    background-color: @background-light;
    border-radius: 2px;
}

/* ---- Element ---- */
element {
    orientation: vertical;
    background-color: @background-light;
    padding: 16px 0px;
    spacing: 10px;
    border-radius: 12px;
    cursor: pointer;
    margin: 2px;
}

element normal.normal {
    background-color: @background-light;
    text-color: @foreground-alt;
}

element alternate.normal {
    background-color: @background-light;
    text-color: @foreground-alt;
}

element selected.normal {
    background-color: @background-light;
    text-color: @primary;
    border: 2px;
    border-color: @primary;
}

element-icon {
    size: 42px;
    background-color: transparent;
    horizontal-align: 0.5;
    padding: 0 0 8px 0;
}

element-text {
    font: "Roboto 11";
    background-color: transparent;
    text-color: inherit;
    horizontal-align: 0.5;
    vertical-align: 0.5;
    padding: 0 12px;
}

/* ---- Pinned Bar ---- */
pinned-bar {
    background-color: @background-alt;
    orientation: horizontal;
    children: [pinned-apps, pinned-folders, pinned-websites];
    padding: 12px;
    spacing: 16px;
    border-radius: 0 0 12px 12px;
}

pinned-apps, pinned-folders, pinned-websites {
    background-color: transparent;
    orientation: horizontal;
    spacing: 10px;
}

pinned-item {
    background-color: @background-light;
    text-color: @foreground;
    padding: 8px;
    border-radius: 12px;
    cursor: pointer;
}

pinned-item selected {
    background-color: @primary-dark;
    text-color: @foreground;
}

/* ---- Message ---- */
message {
    padding: 16px;
    background-color: @background-alt;
    text-color: @foreground;
    border-radius: 12px;
}

textbox {
    background-color: transparent;
    text-color: @foreground;
}
EOL

# Install the pinned script
echo -e "${BLUE}Installing pinned items script...${NC}"
cat >~/.config/rofi/scripts/pinned.sh <<'EOL'
#!/bin/bash

# Pinned.sh - Script to handle pinned apps, folders and websites in Rofi
# Place this in ~/.config/rofi/scripts/pinned.sh and make it executable with: chmod +x ~/.config/rofi/scripts/pinned.sh

# Config file location
CONFIG_FILE="$HOME/.config/rofi/pinned_items.conf"

# Create config if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << CONFEOF
# Pinned items configuration
# Format: TYPE|NAME|ICON|ACTION
# TYPE: app, folder, or url
# NAME: Display name
# ICON: Icon path or icon name
# ACTION: Command to execute

# Apps (first row in pinned section)
app|Firefox|firefox|firefox
app|Terminal|terminal|alacritty
app|Files|system-file-manager|thunar
app|VS Code|code|code
app|Settings|preferences-system|gnome-control-center

# Folders (second row in pinned section)
folder|Documents|folder-documents|xdg-open ~/Documents
folder|Downloads|folder-downloads|xdg-open ~/Downloads
folder|Music|folder-music|xdg-open ~/Music
folder|Pictures|folder-pictures|xdg-open ~/Pictures
folder|Videos|folder-videos|xdg-open ~/Videos

# URLs (third row in pinned section)
url|GitHub|github|xdg-open https://github.com
url|Reddit|reddit|xdg-open https://reddit.com
url|Twitter|twitter|xdg-open https://twitter.com
url|YouTube|youtube|xdg-open https://youtube.com
url|Gmail|mail-unread|xdg-open https://mail.google.com
CONFEOF
fi

# Function to get icon
get_icon() {
    local icon="$1"
    # If icon is a path and exists, use it
    if [[ -f "$icon" ]]; then
        echo "$icon"
    else
        # Otherwise assume it's an icon name
        echo "$icon"
    fi
}

# If no argument provided, display menu
if [ -z "$1" ]; then
    # Read config file and format for rofi
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        
        IFS='|' read -r type name icon action <<< "$line"
        icon=$(get_icon "$icon")
        echo -en "$name\0icon\x1f$icon\n"
    done < "$CONFIG_FILE"
else
    # Handle selection
    selected="$1"
    
    # Find the matching line in the config file
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        
        IFS='|' read -r type name icon action <<< "$line"
        if [ "$name" = "$selected" ]; then
            # Execute the action
            eval "$action" &
            exit 0
        fi
    done < "$CONFIG_FILE"
fi
EOL

# Make the scripts executable
echo -e "${BLUE}Making scripts executable...${NC}"
chmod +x ~/.config/rofi/scripts/pinned.sh

echo -e "${GREEN}Configuration successfully installed!${NC}"
echo -e "${BLUE}You can now start the enhanced Rofi with: ${GREEN}rofi -show drun${NC}"
echo -e "${BLUE}The pinned items can be accessed via the mode switcher or directly with: ${GREEN}rofi -show pinned${NC}"
echo ""
echo -e "${BLUE}Configuration files:${NC}"
echo -e "- Main config: ${GREEN}~/.config/rofi/config.rasi${NC}"
echo -e "- Pinned items: ${GREEN}~/.config/rofi/pinned_items.conf${NC}"
echo ""
echo -e "${BLUE}To customize your pinned items:${NC}"
echo -e "Edit the pinned items in ${GREEN}~/.config/rofi/pinned_items.conf${NC}"
echo -e "Format: TYPE|NAME|ICON|ACTION"
echo -e "- TYPE: app, folder, or url"
echo -e "- NAME: Display name"
echo -e "- ICON: Icon name or path"
echo -e "- ACTION: Command to execute"
