#!/usr/bin/env bash
# Author: Rich Lewis - GitHub: @RichLewis007
# ============================================================
# tui-menus.sh - Toolkit to easily add TUI menus to your scripts.
#
# Features:
#   - Colorful log helpers: log_info, log_ok, log_warn, log_error
#   - Confirm helper: confirm "Prompt"
#   - Spinner helpers: spinner_start, spinner_stop, run_with_spinner
#   - Simple config: cfg_get / cfg_set for KEY=VALUE files
#   - Menus: pick_option (uses fzf, then gum, then basic numbered menu)
#   - Pages: ui_run_page for nested menu "screens"
# ============================================================

# ------------------------------------------------------------
# Colors
# ------------------------------------------------------------
COLOR_RED="\033[31m"
COLOR_GREEN="\033[32m"
COLOR_YELLOW="\033[33m"
COLOR_BLUE="\033[34m"
COLOR_MAGENTA="\033[35m"
COLOR_CYAN="\033[36m"
COLOR_BOLD="\033[1m"
COLOR_DIM="\033[2m"
COLOR_RESET="\033[0m"

# ------------------------------------------------------------
# Logging helpers
# ------------------------------------------------------------
log_info() {
  printf "%b[INFO]%b %s\n" \
    "${COLOR_BLUE}${COLOR_BOLD}" "${COLOR_RESET}" "$*"
}

log_ok() {
  printf "%b[ OK ]%b %s\n" \
    "${COLOR_GREEN}${COLOR_BOLD}" "${COLOR_RESET}" "$*"
}

log_warn() {
  printf "%b[WARN]%b %s\n" \
    "${COLOR_YELLOW}${COLOR_BOLD}" "${COLOR_RESET}" "$*"
}

log_error() {
  printf "%b[ERROR]%b %s\n" \
    "${COLOR_RED}${COLOR_BOLD}" "${COLOR_RESET}" "$*"
}

# ------------------------------------------------------------
# Spinner helpers
# ------------------------------------------------------------
_UI_SPINNER_PID=""

spinner_start() {
  # Usage: spinner_start "Message..."
  # Only show spinner if stdout is a TTY
  if ! [ -t 1 ]; then
    return 0
  fi

  local msg="$1"
  local frames='-\|/'
  local i=0

  printf "%s " "$msg"

  while true; do
    local frame="${frames:i++%4:1}"
    printf "\r%s %s" "$msg" "$frame"
    sleep 0.1
  done &

  _UI_SPINNER_PID=$!
}

spinner_stop() {
  # Usage: spinner_stop [status]
  local status=${1:-0}

  if [[ -n "${_UI_SPINNER_PID:-}" ]]; then
    kill "$_UI_SPINNER_PID" 2>/dev/null || true
    wait "$_UI_SPINNER_PID" 2>/dev/null || true
    _UI_SPINNER_PID=""
  fi

  # Clear spinner line if TTY
  if [ -t 1 ]; then
    printf "\r\033[K"
  fi

  return "$status"
}

run_with_spinner() {
  # Usage: run_with_spinner "Message..." command arg1 arg2 ...
  local msg="$1"; shift

  if [ $# -eq 0 ]; then
    log_error "run_with_spinner: no command given"
    return 1
  fi

  # Non interactive: no spinner, but still log
  if ! [ -t 1 ]; then
    log_info "$msg"
    "$@"
    local status=$?
    if [ $status -eq 0 ]; then
      log_ok "$msg"
    else
      log_error "$msg (failed, exit $status)"
    fi
    return $status
  fi

  spinner_start "$msg"
  "$@"
  local status=$?
  spinner_stop "$status"

  if [ $status -eq 0 ]; then
    log_ok "$msg"
  else
    log_error "$msg (failed, exit $status)"
  fi

  return $status
}

# ------------------------------------------------------------
# Simple KEY=VALUE config helpers
# Default config file: $HOME/.config/tui-menus/config.txt
# You can override with CFG_DEFAULT_FILE in the environment.
# ------------------------------------------------------------
CFG_DEFAULT_FILE="${CFG_DEFAULT_FILE:-$HOME/.config/tui-menus/config.txt}"

cfg_get() {
  # Usage: cfg_get KEY [FILE]
  local key="$1"
  local file="${2:-$CFG_DEFAULT_FILE}"

  [ -n "$key" ] || { log_error "cfg_get: missing key"; return 1; }
  [ -f "$file" ] || return 1

  local line
  while IFS= read -r line; do
    case "$line" in
      ''|'#'*) continue ;;
      "$key="*)
        printf "%s\n" "${line#*=}"
        return 0
        ;;
    esac
  done < "$file"

  return 1
}

cfg_set() {
  # Usage: cfg_set KEY VALUE [FILE]
  local key="$1"
  local value="$2"
  local file="${3:-$CFG_DEFAULT_FILE}"

  [ -n "$key" ] || { log_error "cfg_set: missing key"; return 1; }

  local dir
  dir=$(dirname "$file")
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir" || {
      log_error "cfg_set: cannot create config dir '$dir'"
      return 1
    }
  fi

  local tmp
  tmp="${file}.tmp.$$"
  local found=0
  local line

  if [ -f "$file" ]; then
    while IFS= read -r line; do
      case "$line" in
        "$key="*)
          printf "%s=%s\n" "$key" "$value" >> "$tmp"
          found=1
          ;;
        *)
          printf "%s\n" "$line" >> "$tmp"
          ;;
      esac
    done < "$file"
  fi

  if [ $found -eq 0 ]; then
    printf "%s=%s\n" "$key" "$value" >> "$tmp"
  fi

  mv "$tmp" "$file"
  return 0
}

# ------------------------------------------------------------
# Confirmation
# ------------------------------------------------------------
confirm() {
  local prompt="${1:-Are you sure?} [y/N] "
  local reply
  printf "%s" "$prompt"
  read -r reply
  case "$reply" in
    y|Y|yes|YES) return 0 ;;
    *)           return 1 ;;
  esac
}

# ------------------------------------------------------------
# Basic numbered menu (fallback)
#   - Sets REPLY to index (0 based) on success.
#   - Returns 0 on success, 1 on "q".
# ------------------------------------------------------------
menu_basic() {
  local prompt="$1"; shift
  local options=("$@")
  local count=${#options[@]}
  local i choice
  local border="============================================================"

  if (( count == 0 )); then
    log_error "menu_basic called with no options"
    return 1
  fi

  while true; do
    printf "\n%s\n" "$border"
    printf "%b%s%b\n" "$COLOR_BOLD" "$prompt" "$COLOR_RESET"
    printf "%s\n" "$border"
    for i in "${!options[@]}"; do
      printf "  %b%2d)%b %s\n" "$COLOR_CYAN" "$((i+1))" "$COLOR_RESET" "${options[$i]}"
    done
    printf "  %b q)%b Quit\n" "$COLOR_RED" "$COLOR_RESET"
    printf "%s\n" "$border"

    printf "\nChoose: "
    if ! read -r choice; then
      log_warn "EOF on input, exiting menu."
      return 1
    fi

    case "$choice" in
      q|Q) return 1 ;;
      ''|*[!0-9]*) log_warn "Please enter a number or q."; continue ;;
    esac

    if (( choice >= 1 && choice <= count )); then
      REPLY=$((choice-1))
      return 0
    else
      log_warn "Invalid choice."
    fi
  done
}

# ------------------------------------------------------------
# Command detection helpers
# ------------------------------------------------------------
_ui_have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

_ui_have_gum() { _ui_have_cmd gum; }
_ui_have_fzf() { _ui_have_cmd fzf; }

# ------------------------------------------------------------
# gum and fzf menus
#
# Both accept a header and a prompt line:
#   _ui_menu_gum "Header" "Prompt" options...
#   _ui_menu_fzf "Header" "Prompt" options...
# ------------------------------------------------------------
_ui_menu_gum() {
  local header="$1"; shift
  local prompt_line="$1"; shift
  local options=("$@")

  local combined_header
  if [[ -n "$prompt_line" && "$prompt_line" != "$header" ]]; then
    combined_header="${header}\n${prompt_line}"
  else
    combined_header="$header"
  fi

  # Add "Quit" option to match the behavior of menu_basic
  local options_with_quit=("${options[@]}" "Quit")

  # Calculate height to ensure all options (including Quit) are accessible
  # Use a height that allows gum to show and scroll through all items
  local option_count=${#options_with_quit[@]}
  # Set height high enough to accommodate all items with scrolling
  # Use option count + padding to ensure all items including Quit are accessible
  local menu_height=$((option_count + 5))
  # Use terminal height as upper limit, but ensure we can scroll through all items
  local term_height=${LINES:-$(tput lines 2>/dev/null || echo 24)}
  # Don't exceed terminal height too much, but allow enough for scrolling
  if (( menu_height > term_height + 10 )); then
    menu_height=$((term_height + 10))
  fi
  # Ensure minimum height for usability
  if (( menu_height < 10 )); then
    menu_height=10
  fi

  # Use -- so options starting with "-" are not treated as flags
  # gum choose will display items and allow scrolling to access all including Quit
  gum choose --header "$combined_header" --height="$menu_height" -- "${options_with_quit[@]}"
}

_ui_get_menu_description() {
  # Generate descriptions for menu items
  # This function can be extended to provide detailed descriptions
  local item="$1"
  
  case "$item" in
    "Quit")
      echo "Exit the menu and return to shell"
      ;;
    *"Run Python app"*)
      echo "Launch the Python application in development mode"
      ;;
    *"Dev mode"*|*"Live reload"*)
      echo "Run the app with auto-reload on file changes (uses watchdog)"
      ;;
    *"Qt Designer"*)
      echo "Launch Qt Designer to edit .ui interface files"
      ;;
    *"Build Python package"*)
      echo "Build a Python wheel package using uv"
      ;;
    *"Sync dependencies"*)
      echo "Install/update project dependencies (uv sync --dev)"
      ;;
    *"Type checking"*)
      echo "Run static type checker (mypy or pyright)"
      ;;
    *"Run tests"*)
      echo "Execute test suite (pytest or unittest)"
      ;;
    *"Check linting"*)
      echo "Check code for linting issues (read-only)"
      ;;
    *"Fix linting"*)
      echo "Automatically fix linting issues where possible"
      ;;
    *"Check formatting"*)
      echo "Check if code is properly formatted (read-only)"
      ;;
    *"Fix formatting"*)
      echo "Automatically format code to style guidelines"
      ;;
    *"Cleanup"*|*"cache"*)
      echo "Remove cache directories and temporary files"
      ;;
    *"environment info"*)
      echo "Show project environment information and Python version"
      ;;
    *"Briefcase"*)
      echo "Open Briefcase packaging submenu for building distributables"
      ;;
    *)
      # Default: use the item label as description
      echo "$item"
      ;;
  esac
}

_ui_colorize_ruff() {
  # Add red color to "Ruff" in menu items
  local item="$1"
  # Replace "Ruff" with red-colored "Ruff" using ANSI color codes
  # Use sed to replace while preserving the rest of the text
  echo "$item" | sed "s/Ruff/${COLOR_RED}Ruff${COLOR_RESET}/g"
}

_ui_menu_fzf() {
  local header="$1"; shift
  local prompt_line="$1"; shift
  local options=("$@")

  # Colorize keywords in menu items: Ruff (red), pytest (blue), pyright (green), unittest (orange), Run Python app (purple), dev mode (yellow background)
  local colored_options=()
  local i
  # Use actual ANSI escape sequences for colors
  local red_code=$'\033[31m'
  local blue_code=$'\033[34m'
  local green_code=$'\033[32m'
  local orange_code=$'\033[33m'  # Yellow/orange
  local purple_code=$'\033[35m'  # Magenta (closest to purple)
  local yellow_bg_code=$'\033[43m'  # Yellow background
  local reset_code=$'\033[0m'
  
  for i in "${!options[@]}"; do
    local item="${options[$i]}"
    local colored_item="$item"
    
    # Apply color replacements in order (be careful with overlapping text)
    # Replace longer patterns first to avoid partial matches
    if [[ "$colored_item" == *"pyright"* ]]; then
      colored_item="${colored_item//pyright/${green_code}pyright${reset_code}}"
    fi
    if [[ "$colored_item" == *"pytest"* ]]; then
      colored_item="${colored_item//pytest/${blue_code}pytest${reset_code}}"
    fi
    if [[ "$colored_item" == *"unittest"* ]]; then
      colored_item="${colored_item//unittest/${orange_code}unittest${reset_code}}"
    fi
    if [[ "$colored_item" == *"Ruff"* ]]; then
      colored_item="${colored_item//Ruff/${red_code}Ruff${reset_code}}"
    fi
    # Match "Run Python app" specifically (not just "Run")
    if [[ "$colored_item" == *"Run Python app"* ]]; then
      colored_item="${colored_item//Run Python app/${purple_code}Run Python app${reset_code}}"
    fi
    # Match "dev mode" (case-insensitive) with yellow background
    # Replace "Dev mode" or "dev mode" with yellow background version
    if [[ "$colored_item" == *"ev mode"* ]] || [[ "$colored_item" == *"EV MODE"* ]]; then
      colored_item=$(echo "$colored_item" | sed "s/\([Dd][Ee][Vv]\) \([Mm][Oo][Dd][Ee]\)/${yellow_bg_code}\1 \2${reset_code}/i")
    fi
    
    colored_options+=("$colored_item")
  done
  
  # Add "Quit" option to match the behavior of menu_basic
  local options_with_quit=("${options[@]}" "Quit")
  local colored_options_with_quit=("${colored_options[@]}" "Quit")

  local fzf_header="$header"
  local fzf_prompt="$prompt_line"
  if [[ -z "$fzf_prompt" ]]; then
    fzf_prompt="$fzf_header"
  fi

  # Create a preview command that shows description in right column
  # Export the function so it's available in fzf's preview subprocess
  export -f _ui_get_menu_description
  # Need to strip ANSI codes from {} for description lookup
  local preview_cmd='_ui_get_menu_description "$(echo {} | sed "s/\x1b\[[0-9;]*m//g")"'

  # Use colored options for display, but we need to map back to original for selection
  # fzf will return the colored version, so we need to strip colors when matching
  local choice
  choice=$(printf "%s\n" "${colored_options_with_quit[@]}" | fzf \
    --header="$fzf_header" \
    --prompt="${fzf_prompt} " \
    --height=100% \
    --border \
    --reverse \
    --info=hidden \
    --cycle \
    --preview="$preview_cmd" \
    --preview-window=right:40%:wrap \
    --ansi) || return 1
  
  # Strip ANSI color codes from the choice to match original
  choice=$(echo "$choice" | sed "s/\x1b\[[0-9;]*m//g")
  echo "$choice"
}

# ------------------------------------------------------------
# Option picker
#
# pick_option "Prompt" "Opt 1" "Opt 2" ...
#
# If the prompt contains a newline:
#   "Header line\nPrompt line"
# the first line is used as header, the second as the interactive prompt.
#
# Order:
#   1. fzf (typing filters, border, best scrolling)
#   2. basic numbered menu (reliable, shows numbers, includes Quit)
# Note: gum is skipped due to display/scroll issues with many items
# ------------------------------------------------------------
pick_option() {
  local prompt="$1"; shift
  local options=("$@")
  local choice

  if (( ${#options[@]} == 0 )); then
    log_error "pick_option called with no options"
    return 1
  fi

  # Split into header and prompt_line on first newline
  local header prompt_line
  header="${prompt%%$'\n'*}"
  if [[ "$prompt" == *$'\n'* ]]; then
    prompt_line="${prompt#*$'\n'}"
  else
    prompt_line="$prompt"
  fi

  # Prefer fzf for fuzzy type-to-search menus (best scrolling support)
  if _ui_have_fzf; then
    choice=$(_ui_menu_fzf "$header" "$prompt_line" "${options[@]}") || return 1
    # If "Quit" was selected, return 1 to match menu_basic behavior
    if [[ "$choice" == "Quit" ]]; then
      return 1
    fi
    printf "%s\n" "$choice"
    return 0
  fi

  # Fallback to basic numbered menu (shows numbers, includes Quit)
  if menu_basic "$prompt" "${options[@]}"; then
    printf "%s\n" "${options[$REPLY]}"
    return 0
  else
    return 1
  fi
}

# ============================================================
# Page concept (nested menus)
#
# Each page calls ui_run_page with entries:
#   "Label::HandlerFunction"
#
# Special handler names:
#   BACK  -> return to previous page
#   QUIT  -> exit 0
# ============================================================
ui_run_page() {
  local title="$1"; shift
  local entries=("$@")

  if (( ${#entries[@]} == 0 )); then
    log_error "ui_run_page called with no entries"
    return 1
  fi

  local labels=()
  local handlers=()
  local e label handler

  # Split "Label::Handler"
  for e in "${entries[@]}"; do
    label=${e%%::*}
    handler=${e##*::}
    labels+=("$label")
    handlers+=("$handler")
  done

  while true; do
    local choice
    choice=$(pick_option "$title" "${labels[@]}") || {
      log_warn "Menu cancelled: $title"
      return 0
    }

    # Find matching handler
    local i
    handler=""
    for i in "${!labels[@]}"; do
      if [[ "${labels[$i]}" == "$choice" ]]; then
        handler="${handlers[$i]}"
        break
      fi
    done

    if [[ -z "$handler" ]]; then
      log_error "No handler found for choice '$choice'"
      continue
    fi

    case "$handler" in
      BACK)
        log_info "Returning from page: $title"
        return 0
        ;;
      QUIT)
        log_info "Exiting from page: $title"
        exit 0
        ;;
    esac

    if declare -f "$handler" >/dev/null 2>&1; then
      "$handler" || log_warn "Handler '$handler' returned non zero"
    else
      log_error "Handler function '$handler' not found for choice '$choice'"
    fi
  done
}
