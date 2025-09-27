#!/bin/bash

# A robust utility to scrape and download files based on a URL and a regex pattern.
#
# This script fetches the content of a URL, extracts all potential hyperlinks,
# filters them against a user-provided regex pattern, and then downloads
# the matching files.
#
# Dependencies: curl, wget, GNU grep (or a grep that supports -P)
#
# --- Strict Mode & Error Handling ---
# set -e: Exit immediately if a command exits with a non-zero status.
# set -u: Treat unset variables as an error when substituting.
# set -o pipefail: The return value of a pipeline is the status of the last
#                  command to exit with a non-zero status.

# --- Configuration & Colors ---
# Use colors for output, but disable if stdout is not a tty (e.g., piping to a file)
if [ -t 1 ] && [ -n "${TERM:-}" ] && [ "${TERM:-}" != "dumb" ]; then
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    RED=$(tput setaf 1)
    BLUE=$(tput setaf 4)
    BOLD=$(tput bold)
    NC=$(tput sgr0) # No Color
else
    GREEN=""
    YELLOW=""
    RED=""
    BLUE=""
    BOLD=""
    NC=""
fi

# --- Functions ---

# Function to print colored messages
# Using printf for better portability and consistency
info() { printf "%s\n" "${BLUE}${BOLD}[INFO]${NC} $1"; }
success() { printf "%s\n" "${GREEN}${BOLD}[SUCCESS]${NC} $1"; }
warn() { printf "%s\n" "${YELLOW}${BOLD}[WARNING]${NC} $1"; }
error() { printf "%s\n" "${RED}${BOLD}[ERROR]${NC} $1" >&2; }

# Function to display usage information
show_usage() {
    cat <<EOF
${BOLD}Web Scraper & Downloader Utility${NC}

A script to scrape a webpage for links and download files matching a specific pattern.

${BOLD}USAGE:${NC}
  $0 -u <URL> -d <OUTPUT_DIR> -p <PATTERN> [OPTIONS]

${BOLD}REQUIRED ARGUMENTS:${NC}
  -u, --url <URL>           The target URL to scrape.
  -d, --dir <OUTPUT_DIR>    The directory where files will be saved.
  -p, --pattern <PATTERN>   The regex pattern to match file URLs.

${BOLD}OPTIONS:${NC}
  -e, --engine <ENGINE>     Regex engine for the pattern: 'E' for Extended (default), 'P' for PCRE.
  -n, --dry-run             List the files that would be downloaded without downloading them.
  -f, --force               Force download, overwriting if the file already exists.
  -A, --user-agent <AGENT>  Specify a custom User-Agent for curl and wget.
  -v, --verbose             Enable verbose output for curl and wget.
  -h, --help                Display this help message and exit.

${BOLD}DETAILS:${NC}
  - The script first extracts all absolute URLs from the page source.
  - It then filters these URLs against your pattern.
  - Query strings (e.g., ?v=123) are automatically stripped from filenames before saving.

${BOLD}EXAMPLE:${NC}
  $0 -u "https://512pixels.net/projects/default-mac-wallpapers-in-5k/" \\
     -d "macos_wallpapers" \\
     -p 'Dark.*6K\.png' \\
     --user-agent "MyScraper/1.0"
EOF
}

# --- Argument Parsing ---
# Set default values for options
URL=""
OUT_DIR=""
PATTERN=""
DRY_RUN=false
FORCE_DOWNLOAD=false
VERBOSE=false
USER_AGENT="Bash-Scraper/1.0"
REGEX_ENGINE="E" # Default to Extended Regex (more portable)

# Parse command-line arguments using a more robust loop
while [[ $# -gt 0 ]]; do
    case "$1" in
    -u | --url)
        if [[ -z "${2:-}" || "${2:0:1}" == "-" ]]; then
            error "Option '$1' requires an argument." >&2
            exit 1
        fi
        URL="$2"
        shift 2
        ;;
    -d | --dir)
        if [[ -z "${2:-}" || "${2:0:1}" == "-" ]]; then
            error "Option '$1' requires an argument." >&2
            exit 1
        fi
        OUT_DIR="$2"
        shift 2
        ;;
    -p | --pattern)
        if [[ -z "${2:-}" || "${2:0:1}" == "-" ]]; then
            error "Option '$1' requires an argument." >&2
            exit 1
        fi
        PATTERN="$2"
        shift 2
        ;;
    -e | --engine)
        if [[ -z "${2:-}" || "${2:0:1}" == "-" ]]; then
            error "Option '$1' requires an argument." >&2
            exit 1
        fi
        REGEX_ENGINE=$(echo "$2" | tr '[:lower:]' '[:upper:]')
        if [[ "$REGEX_ENGINE" != "E" && "$REGEX_ENGINE" != "P" ]]; then
            error "Invalid regex engine '$2'. Must be 'E' or 'P'."
            exit 1
        fi
        shift 2
        ;;
    -A | --user-agent)
        if [[ -z "${2:-}" || "${2:0:1}" == "-" ]]; then
            error "Option '$1' requires an argument." >&2
            exit 1
        fi
        USER_AGENT="$2"
        shift 2
        ;;
    -n | --dry-run)
        DRY_RUN=true
        shift 1
        ;;
    -f | --force)
        FORCE_DOWNLOAD=true
        shift 1
        ;;
    -v | --verbose)
        VERBOSE=true
        shift 1
        ;;
    -h | --help)
        show_usage
        exit 0
        ;;
    -*)
        error "Unknown option: $1"
        show_usage
        exit 1
        ;;
    *)
        error "Unexpected argument: $1"
        show_usage
        exit 1
        ;;
    esac
done

# --- Main Logic ---

main() {
    # Validate required arguments
    if [[ -z "$URL" || -z "$OUT_DIR" || -z "$PATTERN" ]]; then
        error "URL (-u), Directory (-d), and Pattern (-p) are mandatory."
        show_usage
        exit 1
    fi

    # Check for dependencies
    local GREP_CMD=""
    for cmd in curl wget grep; do
        if ! command -v "$cmd" &>/dev/null; then
            error "Required command '$cmd' is not installed. Please install it and try again."
            exit 1
        fi
    done

    # Find a grep that supports PCRE (-P) for robust URL extraction
    if grep -qP 'test' <<<'test' &>/dev/null; then
        GREP_CMD="grep"
    elif command -v ggrep &>/dev/null && ggrep -qP 'test' <<<'test' &>/dev/null; then
        info "Default 'grep' does not support PCRE. Found and using 'ggrep'."
        GREP_CMD="ggrep"
    else
        error "A 'grep' with PCRE support (option -P) is required for URL extraction."
        error "Please install GNU grep. On macOS, try: 'brew install grep'"
        exit 1
    fi

    # --- Build Command Options ---
    # -L follows redirects, -k ignores cert errors
    local -a curl_opts=("-k" "-L" "-A" "$USER_AGENT")
    # --no-check-certificate to match curl's -k behavior
    local -a wget_opts=("--no-check-certificate" "-P" "$OUT_DIR" "-U" "$USER_AGENT")

    # Correct verbose logic
    if [[ "$VERBOSE" == true ]]; then
        info "Verbose mode enabled."
        # curl default is verbose, so don't add -s
        wget_opts+=("-v") # -v for verbose output.
    else
        curl_opts+=("-s") # -s for silent curl.
        wget_opts+=("-q") # -q for quiet wget.
    fi

    info "Target URL: $URL"
    info "Output Directory: $OUT_DIR"
    info "Search Pattern: $PATTERN (using engine: $REGEX_ENGINE)"

    info "Ensuring output directory '$OUT_DIR' exists..."
    mkdir -p "$OUT_DIR"

    info "Fetching and parsing page content..."
    local html_content
    if ! html_content=$(curl "${curl_opts[@]}" "$URL"); then
        error "curl failed to fetch the URL. Check URL, network, or SSL certificate issues."
        exit 1
    fi

    # --- Robust URL Extraction ---
    # The `|| true` prevents the script from exiting if grep finds no matches.
    # `mapfile` (or `readarray`) is an efficient way to read lines into an array.
    local -a image_urls
    mapfile -t image_urls < <(echo "$html_content" | "$GREP_CMD" -oP 'https?://[^\s"'\''\`<>]+' | grep "-${REGEX_ENGINE}" "$PATTERN" || true)

    local total_urls=${#image_urls[@]}

    if [[ "$total_urls" -eq 0 ]]; then
        warn "No URLs found matching the pattern '$PATTERN'. Exiting."
        exit 0
    fi

    info "Found $total_urls files to process."

    if [[ "$DRY_RUN" == true ]]; then
        info "Dry run enabled. The following files would be downloaded:"
        printf "  %s\n" "${image_urls[@]}"
        exit 0
    fi

    # --- Download Loop ---
    local download_count=0
    local skipped_count=0
    local i=0
    for image_url in "${image_urls[@]}"; do
        ((i++))
        # Strip query string for a clean filename
        local clean_url="${image_url%%\?*}"
        local filename
        filename=$(basename "$clean_url")

        printf -- "--------------------------------------------------\n"
        info "[${i}/${total_urls}] Processing: ${filename}"

        # This check is more efficient than `wget --no-clobber` as it avoids making a network request.
        if [[ "$FORCE_DOWNLOAD" == false && -f "$OUT_DIR/$filename" ]]; then
            warn "File already exists. Skipped. (Use -f to force download)"
            ((skipped_count++))
            continue
        fi

        info "Downloading: $image_url"
        # `wget -O` will overwrite the file if it exists, which is the desired behavior for --force.
        if wget "${wget_opts[@]}" -O "$OUT_DIR/$filename" "$image_url"; then
            success "Downloaded successfully."
            ((download_count++))
        else
            # With `set -e`, the script exits on error, so this message provides context.
            error "Download failed for: $image_url (wget exit code: $?)"
        fi
    done

    printf -- "--------------------------------------------------\n"
    success "Done. Downloaded $download_count new files."
    if ((skipped_count > 0)); then
        warn "$skipped_count files were already present and were skipped."
    fi
    info "All files are saved in '$OUT_DIR'."
}

# Run the main function
main
