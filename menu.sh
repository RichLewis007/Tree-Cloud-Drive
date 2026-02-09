#!/usr/bin/env bash
# Author: Rich Lewis - GitHub: @RichLewis007
# Development menu script for Python projects
# Auto-detects project information from pyproject.toml
# Uses tui-menus.sh for TUI menu functionality
#

set -uo pipefail

# Script metadata constants
readonly MENU_VERSION="1.3"

# Source the tui-menus library (provides TUI menu functions like ui_run_page, log_info, etc.)
# Try multiple locations for portability:
# 1. Same directory as script (for bundled/copied projects)
# 2. Scripts directory (alternative location)
# 3. User's utils directory (for shared library setup)
# 4. Fallback to inline minimal functions if not found
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/tui-menus.sh" ]; then
    source "$SCRIPT_DIR/tui-menus.sh"
elif [ -f "$SCRIPT_DIR/scripts/tui-menus.sh" ]; then
    source "$SCRIPT_DIR/scripts/tui-menus.sh"
elif [ -f "$HOME/utils/tui-menus.sh" ]; then
    source "$HOME/utils/tui-menus.sh"
else
    # ============================================================================
    # MINIMAL FALLBACK UI FUNCTIONS
    # ============================================================================
    # If tui-menus.sh is not found, provide minimal implementations so menu still works.
    # These are simplified versions - full tui-menus.sh provides better UI with fzf/gum support.
    
    # Basic color constants
    COLOR_RED="\033[31m"
    COLOR_GREEN="\033[32m"
    COLOR_YELLOW="\033[33m"
    COLOR_BLUE="\033[34m"
    COLOR_BOLD="\033[1m"
    COLOR_DIM="\033[2m"
    COLOR_RESET="\033[0m"
    
    # Minimal logging functions
    log_info() {
        printf "%b[INFO]%b %s\n" "${COLOR_BLUE}${COLOR_BOLD}" "${COLOR_RESET}" "$*"
    }
    
    log_ok() {
        printf "%b[ OK ]%b %s\n" "${COLOR_GREEN}${COLOR_BOLD}" "${COLOR_RESET}" "$*"
    }
    
    log_warn() {
        printf "%b[WARN]%b %s\n" "${COLOR_YELLOW}${COLOR_BOLD}" "${COLOR_RESET}" "$*"
    }
    
    log_error() {
        printf "%b[ERROR]%b %s\n" "${COLOR_RED}${COLOR_BOLD}" "${COLOR_RESET}" "$*"
    }
    
    # Minimal confirmation function
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
    
    # Minimal menu function (basic numbered menu)
    # Uses global variable PICK_OPTION_RESULT to avoid subshell stdin issues
    pick_option() {
        local prompt="$1"; shift
        local options=("$@")
        local border="============================================================"
        local count=${#options[@]}
        local i choice
        
        PICK_OPTION_RESULT=""  # Clear result
        
        if (( count == 0 )); then
            log_error "pick_option called with no options"
            return 1
        fi
        
        while true; do
            # Print menu to stderr so it's always visible, even when called via command substitution
            printf "\n%s\n" "$border" >&2
            printf "%b%s%b\n" "$COLOR_BOLD" "$prompt" "$COLOR_RESET" >&2
            printf "%s\n" "$border" >&2
            for i in "${!options[@]}"; do
                printf "  %b%2d)%b %s\n" "$COLOR_BLUE" "$((i+1))" "$COLOR_RESET" "${options[$i]}" >&2
            done
            printf "  %b Q)%b Quit\n" "$COLOR_RED" "$COLOR_RESET" >&2
            printf "%s\n" "$border" >&2
            printf "\nChoose: " >&2  # Print prompt to stderr so it's visible even in command substitution
            # Always read from /dev/tty (controlling terminal) to avoid subshell stdin issues  
            # This works reliably on both macOS and Linux when called via command substitution
            if ! read -r choice </dev/tty 2>/dev/null; then
                # Fallback if /dev/tty fails (shouldn't happen on normal systems)
                if ! read -r choice; then
                    log_warn "EOF on input, exiting menu."
                    return 1
                fi
            fi
            
            case "$choice" in
                q|Q|quit|QUIT) return 1 ;;
                ''|*[!0-9]*) log_warn "Please enter a number or Q to quit."; continue ;;
            esac
            
            if (( choice >= 1 && choice <= count )); then
                PICK_OPTION_RESULT="${options[$((choice-1))]}"
                printf "%s\n" "$PICK_OPTION_RESULT"
                return 0
            else
                log_warn "Invalid choice. Please enter a number between 1 and $count."
            fi
        done
    }
    
    # Minimal ui_run_page function
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
            # Call pick_option and capture output (it still prints to stdout for compatibility)
            # but also sets PICK_OPTION_RESULT for our use
            choice=$(pick_option "$title" "${labels[@]}") || {
                log_warn "Menu cancelled: $title"
                return 0
            }
            # Use the global variable if command substitution didn't capture it properly
            [[ -z "$choice" ]] && choice="$PICK_OPTION_RESULT"
            [[ -z "$choice" ]] && continue
            
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
    
    log_warn "tui-menus.sh not found, using minimal fallback UI (basic numbered menus)"
    log_info "For better UI with fzf/gum support, install tui-menus.sh in one of:"
    log_info "  - $SCRIPT_DIR/tui-menus.sh"
    log_info "  - $SCRIPT_DIR/scripts/tui-menus.sh"
    log_info "  - $HOME/utils/tui-menus.sh"
    echo ""
fi

# Change to project root directory (already set above)
cd "$SCRIPT_DIR"

# ============================================================================
# AUTO-DETECTION: Project Information from pyproject.toml
# ============================================================================
# This script automatically detects project configuration to adapt to any project.
# All detection happens at startup, so the script works without hardcoded values.

if [ -f "pyproject.toml" ]; then
    # Detect project name from [project] section
    # Extract name value from: name = "tree-cloud-drive" or name = 'project-name'
    # Use awk for more reliable extraction (removes quotes and whitespace)
    PROJECT_NAME=$(awk -F'=' '/^name[[:space:]]*=/ {gsub(/["'\''[:space:]]/, "", $2); print $2; exit}' pyproject.toml 2>/dev/null || echo "unknown")
    
    # Detect project version from [project] section
    # Extract version value from: version = "0.2.0" or version = '0.2.0'
    # Use awk for more reliable extraction
    PROJECT_VERSION=$(awk -F'=' '/^version[[:space:]]*=/ {gsub(/["'\''[:space:]]/, "", $2); print $2; exit}' pyproject.toml 2>/dev/null || echo "unknown")
    
    # Detect entry point script name from [project.scripts] section
    # Takes the first script entry (format: script_name = "module:function")
    # Regex allows letters, numbers, hyphens, and underscores in script names
    ENTRY_POINT=$(grep -A 10 '\[project.scripts\]' pyproject.toml | grep -E '^\s*[a-zA-Z0-9_-]+\s*=' | head -1 | cut -d'=' -f1 | tr -d ' ' || echo "")
    
    # Auto-detect app bundle location (for Briefcase-packaged apps)
    # Tries multiple common locations in priority order:
    # 1. build/app/macos/app/${PROJECT_NAME}.app (project-specific)
    # 2. build/app/macos/app/App.app (generic)
    # 3. dist/${PROJECT_NAME}.app (alternative location)
    # Empty string if none found (script handles this gracefully)
    if [ -d "build/app/macos/app/${PROJECT_NAME}.app" ]; then
        APP_BUNDLE="build/app/macos/app/${PROJECT_NAME}.app"
    elif [ -d "build/app/macos/app/App.app" ]; then
        APP_BUNDLE="build/app/macos/app/App.app"
    elif [ -d "dist/${PROJECT_NAME}.app" ]; then
        APP_BUNDLE="dist/${PROJECT_NAME}.app"
    else
        APP_BUNDLE=""
    fi
else
    # Fallback values if pyproject.toml not found
    PROJECT_NAME="unknown-project"
    PROJECT_VERSION="unknown"
    ENTRY_POINT=""
    APP_BUNDLE=""
fi

# ============================================================================
# AUTO-DETECTION: Determine App Run Command
# ============================================================================
# Intelligently determines how to run the application based on project structure.
# Priority order:
# 1. Use installed entry point script (if available in PATH)
# 2. Use uv run with entry point name (from pyproject.toml)
# 3. Use Python module format (python -m module_name)
# 4. Fallback to common locations (src/app/main.py, etc.)
#
# Note: ${PROJECT_NAME//-/_} converts hyphens to underscores for module names
#       (e.g., "tree-cloud-drive" becomes "tree_cloud_drive")

if [ -n "$ENTRY_POINT" ] && command -v "$ENTRY_POINT" >/dev/null 2>&1; then
    # Use the installed entry point script (already in PATH)
    RUN_APP_CMD="$ENTRY_POINT"
elif [ -n "$ENTRY_POINT" ]; then
    # Use uv run with the entry point name (installs/uses virtual env)
    RUN_APP_CMD="uv run $ENTRY_POINT"
elif [ -f "src/${PROJECT_NAME//-/_}/__main__.py" ]; then
    # Use Python module format (standard Python package structure)
    MODULE_NAME="${PROJECT_NAME//-/_}"
    RUN_APP_CMD="uv run python -m $MODULE_NAME"
else
    # Fallback: try to find main.py in common locations
    if [ -f "src/${PROJECT_NAME//-/_}/__main__.py" ]; then
        RUN_APP_CMD="uv run python -m ${PROJECT_NAME//-/_}"
    elif [ -f "src/app/main.py" ]; then
        RUN_APP_CMD="uv run python src/app/main.py"
    else
        # Last resort: assume module format will work
        RUN_APP_CMD="uv run python -m ${PROJECT_NAME//-/_}"
    fi
fi

# ============================================================================
# AUTO-DETECTION: Development Tools
# ============================================================================
# Detects which development tools are available in the project.
# Checks dependencies, configuration files, and command availability.
# This allows the menu to adapt to different tooling choices.

# Type checker detection (mypy vs pyright)
HAS_MYPY=false
HAS_PYRIGHT=false

# Check pyproject.toml for type checkers in dependencies
if [ -f "pyproject.toml" ]; then
    if grep -qiE '(mypy|mypy\[|^mypy\s*=)' pyproject.toml 2>/dev/null; then
        HAS_MYPY=true
    fi
    if grep -qiE '(pyright|pyright>=|pyright==)' pyproject.toml 2>/dev/null; then
        HAS_PYRIGHT=true
    fi
    # Also check dependency groups (like [dependency-groups.dev])
    if grep -qiE '\[.*dependenc.*\]' pyproject.toml 2>/dev/null; then
        if grep -qiE 'mypy' pyproject.toml 2>/dev/null; then
            HAS_MYPY=true
        fi
        if grep -qiE 'pyright' pyproject.toml 2>/dev/null; then
            HAS_PYRIGHT=true
        fi
    fi
fi

# Check for mypy configuration files
if [ -f ".mypy.ini" ] || [ -f "mypy.ini" ] || [ -f "setup.cfg" ] || \
   grep -qiE '\[tool\.mypy\]' pyproject.toml 2>/dev/null; then
    HAS_MYPY=true
fi

# Check for pyright configuration files
if [ -f "pyrightconfig.json" ] || [ -f ".pyrightconfig.json" ] || \
   grep -qiE '\[tool\.pyright\]' pyproject.toml 2>/dev/null; then
    HAS_PYRIGHT=true
fi

# Test command availability (check if uv run works, fallback to direct command)
if [ "$HAS_MYPY" = false ] && (uv run mypy --version >/dev/null 2>&1 || command -v mypy >/dev/null 2>&1); then
    HAS_MYPY=true
fi
if [ "$HAS_PYRIGHT" = false ] && (uv run pyright --version >/dev/null 2>&1 || command -v pyright >/dev/null 2>&1); then
    HAS_PYRIGHT=true
fi

# Formatter detection (ruff format vs black)
HAS_RUFF_FORMAT=false
HAS_BLACK=false

if [ -f "pyproject.toml" ]; then
    if grep -qiE '(ruff.*format|\[tool\.ruff\.format\])' pyproject.toml 2>/dev/null || \
       grep -qiE 'ruff' pyproject.toml 2>/dev/null; then
        HAS_RUFF_FORMAT=true
    fi
    if grep -qiE '(black|black\[)' pyproject.toml 2>/dev/null || \
       grep -qiE '\[tool\.black\]' pyproject.toml 2>/dev/null; then
        HAS_BLACK=true
    fi
fi

# Check command availability
if [ "$HAS_RUFF_FORMAT" = false ] && (uv run ruff format --version >/dev/null 2>&1 || command -v ruff >/dev/null 2>&1); then
    HAS_RUFF_FORMAT=true
fi
if [ "$HAS_BLACK" = false ] && (uv run black --version >/dev/null 2>&1 || command -v black >/dev/null 2>&1); then
    HAS_BLACK=true
fi

# Linter detection (ruff check vs flake8 vs pylint)
HAS_RUFF_CHECK=false
HAS_FLAKE8=false
HAS_PYLINT=false

if [ -f "pyproject.toml" ]; then
    if grep -qiE '(ruff|\[tool\.ruff\])' pyproject.toml 2>/dev/null; then
        HAS_RUFF_CHECK=true
    fi
    if grep -qiE '(flake8|flake8\[)' pyproject.toml 2>/dev/null || \
       [ -f ".flake8" ] || [ -f "setup.cfg" ] || \
       grep -qiE '\[tool\.flake8\]' pyproject.toml 2>/dev/null; then
        HAS_FLAKE8=true
    fi
    if grep -qiE '(pylint|pylint\[)' pyproject.toml 2>/dev/null || \
       [ -f ".pylintrc" ] || [ -f "pylintrc" ] || \
       grep -qiE '\[tool\.pylint\]' pyproject.toml 2>/dev/null; then
        HAS_PYLINT=true
    fi
fi

# Check command availability
if [ "$HAS_RUFF_CHECK" = false ] && (uv run ruff check --version >/dev/null 2>&1 || command -v ruff >/dev/null 2>&1); then
    HAS_RUFF_CHECK=true
fi
if [ "$HAS_FLAKE8" = false ] && (uv run flake8 --version >/dev/null 2>&1 || command -v flake8 >/dev/null 2>&1); then
    HAS_FLAKE8=true
fi
if [ "$HAS_PYLINT" = false ] && (uv run pylint --version >/dev/null 2>&1 || command -v pylint >/dev/null 2>&1); then
    HAS_PYLINT=true
fi

# Test runner detection (pytest vs unittest)
HAS_PYTEST=false
# unittest is always available (Python standard library)
HAS_UNITTEST=true

if [ -f "pyproject.toml" ]; then
    if grep -qiE '(pytest|pytest\[|\[tool\.pytest\])' pyproject.toml 2>/dev/null; then
        HAS_PYTEST=true
    fi
fi

# Check pytest command availability
if [ "$HAS_PYTEST" = false ] && (uv run pytest --version >/dev/null 2>&1 || command -v pytest >/dev/null 2>&1); then
    HAS_PYTEST=true
fi

# Package manager detection
HAS_UV=false
HAS_POETRY=false
HAS_PIPENV=false

if command -v uv >/dev/null 2>&1 || uv --version >/dev/null 2>&1; then
    HAS_UV=true
fi
if [ -f "pyproject.toml" ] && grep -qiE '\[tool\.poetry\]' pyproject.toml 2>/dev/null; then
    HAS_POETRY=true
elif command -v poetry >/dev/null 2>&1; then
    HAS_POETRY=true
fi
if [ -f "Pipfile" ] || [ -f "Pipfile.lock" ]; then
    HAS_PIPENV=true
elif command -v pipenv >/dev/null 2>&1; then
    HAS_PIPENV=true
fi

# Helper function to run a command with timing and wait for user input
run_timed_command() {
    local description="$1"
    shift
    local start_time end_time elapsed
    
    log_info "Running: $description"
    start_time=$(date +%s)
    
    # Run the command, capturing both stdout and stderr
    if "$@" 2>&1; then
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        log_ok "Completed in ${elapsed}s: $description"
    else
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        log_error "Failed after ${elapsed}s: $description"
    fi
    
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

# Menu handler functions
handler_run_python_app() {
    # Execute RUN_APP_CMD directly using eval to handle multi-word commands properly
    # (e.g., "uv run tree-cloud-drive" needs to be executed as a single command string)
    local description="Run Python app (development mode)"
    local start_time end_time elapsed
    
    log_info "Running: $description"
    start_time=$(date +%s)
    
    # Use eval to execute the command string, capturing both stdout and stderr
    if eval "$RUN_APP_CMD" 2>&1; then
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        log_ok "Completed in ${elapsed}s: $description"
    else
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        log_error "Failed after ${elapsed}s: $description"
    fi
    
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

handler_qt_designer() {
    log_info "Launching Qt Designer..."
    if [ -f "./qt-designer.sh" ]; then
        ./qt-designer.sh
        log_ok "Qt Designer launched"
    else
        log_error "qt-designer.sh not found in current directory"
    fi
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

handler_build_package() {
    run_timed_command "Build Python package (wheel)" \
        uv build
}

handler_bump_version() {
    local current_version="$PROJECT_VERSION"
    local new_version
    printf "Enter new version (current: %s): " "$current_version"
    read -r new_version
    if [ -z "$new_version" ]; then
        log_warn "No version entered; cancelled."
        return 0
    fi
    if ! [[ "$new_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format. Use X.Y.Z"
        return 1
    fi
    run_timed_command "Bump version to $new_version" \
        python scripts/bump-version.py "$new_version"
}

# ============================================================================
# LINTER HANDLERS
# ============================================================================

handler_ruff_check() {
    if command -v ruff >/dev/null 2>&1; then
        run_timed_command "Ruff: Check linting" \
            ruff check .
    else
        run_timed_command "Ruff: Check linting" \
            uv run ruff check .
    fi
}

handler_ruff_fix() {
    if command -v ruff >/dev/null 2>&1; then
        run_timed_command "Ruff: Fix linting issues" \
            ruff check --fix .
    else
        run_timed_command "Ruff: Fix linting issues" \
            uv run ruff check --fix .
    fi
}

handler_flake8_check() {
    if command -v flake8 >/dev/null 2>&1; then
        run_timed_command "flake8: Check linting" \
            flake8 .
    else
        run_timed_command "flake8: Check linting" \
            uv run flake8 .
    fi
}

handler_pylint_check() {
    # Determine source directory to check
    local src_dir="src"
    if [ ! -d "$src_dir" ] && [ -d "${PROJECT_NAME//-/_}" ]; then
        src_dir="${PROJECT_NAME//-/_}"
    fi
    
    if command -v pylint >/dev/null 2>&1; then
        run_timed_command "pylint: Check linting" \
            pylint "$src_dir"
    else
        run_timed_command "pylint: Check linting" \
            uv run pylint "$src_dir"
    fi
}

# ============================================================================
# FORMATTER HANDLERS
# ============================================================================

handler_ruff_format_check() {
    if command -v ruff >/dev/null 2>&1; then
        run_timed_command "Ruff: Check formatting" \
            ruff format --check .
    else
        run_timed_command "Ruff: Check formatting" \
            uv run ruff format --check .
    fi
}

handler_ruff_format_fix() {
    if command -v ruff >/dev/null 2>&1; then
        run_timed_command "Ruff: Fix formatting" \
            ruff format .
    else
        run_timed_command "Ruff: Fix formatting" \
            uv run ruff format .
    fi
}

handler_black_check() {
    if command -v black >/dev/null 2>&1; then
        run_timed_command "black: Check formatting" \
            black --check .
    else
        run_timed_command "black: Check formatting" \
            uv run black --check .
    fi
}

handler_black_fix() {
    if command -v black >/dev/null 2>&1; then
        run_timed_command "black: Fix formatting" \
            black .
    else
        run_timed_command "black: Fix formatting" \
            uv run black .
    fi
}

handler_dev_live_reload() {
    log_info "Starting dev mode with live reload (Ctrl+C to stop)"
    log_info "Watches for .py and .ui file changes and auto-restarts the app"
    echo ""
    uv run python scripts/dev.py
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

handler_briefcase_clean() {
    if confirm "This will delete build/, macOS/, and dist/ directories. Continue?"; then
        run_timed_command "Briefcase: Clean build artifacts" \
            uv run briefcase clean
            # rm -rf build/ macOS/ dist/
    else
        log_info "Clean cancelled"
    fi
}

handler_briefcase_create() {
    run_timed_command "Briefcase: Create app structure" \
        uv run briefcase create macOS --log
}

handler_briefcase_build() {
    run_timed_command "Briefcase: Build the app" \
        uv run briefcase build macOS --log
    # Copy UI files to app bundle Resources (workaround for resources not being copied)
    # Try common app bundle locations
    BUNDLE_RESOURCES=""
    if [ -n "$APP_BUNDLE" ] && [ -d "${APP_BUNDLE}/Contents/Resources" ]; then
        BUNDLE_RESOURCES="${APP_BUNDLE}/Contents/Resources"
    elif [ -d "build/app/macos/app/App.app/Contents/Resources" ]; then
        BUNDLE_RESOURCES="build/app/macos/app/App.app/Contents/Resources"
    fi
    
    if [ -n "$BUNDLE_RESOURCES" ] && [ -d "ui" ]; then
        log_info "Copying UI files to app bundle..."
        cp -r ui "$BUNDLE_RESOURCES/" 2>/dev/null && \
        log_ok "UI files copied successfully" || \
        log_warn "Failed to copy UI files"
    fi
}

handler_briefcase_test_app() {
    if [ -z "$APP_BUNDLE" ] || [ ! -d "$APP_BUNDLE" ]; then
        log_error "App bundle not found"
        if [ -n "$APP_BUNDLE" ]; then
            log_info "Expected location: $APP_BUNDLE"
        fi
        log_info "Please build the app first (Briefcase menu option 3)"
        printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
        read -n 1 -s
        echo ""
        return 1
    fi
    log_info "Opening app bundle: $APP_BUNDLE"
    open "$APP_BUNDLE"
    log_ok "App launched (check for GUI window)"
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

handler_briefcase_dev() {
    log_info "Starting Briefcase dev mode (Ctrl+C to stop)"
    log_info "This runs the app in development mode with live code reloading"
    echo ""
    uv run briefcase dev
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

handler_briefcase_package() {
    # Ensure UI files are copied before packaging
    BUNDLE_RESOURCES=""
    if [ -n "$APP_BUNDLE" ] && [ -d "${APP_BUNDLE}/Contents/Resources" ]; then
        BUNDLE_RESOURCES="${APP_BUNDLE}/Contents/Resources"
    elif [ -d "build/app/macos/app/App.app/Contents/Resources" ]; then
        BUNDLE_RESOURCES="build/app/macos/app/App.app/Contents/Resources"
    fi
    
    if [ -n "$BUNDLE_RESOURCES" ] && [ -d "ui" ]; then
        cp -r ui "$BUNDLE_RESOURCES/" 2>/dev/null
    fi
    run_timed_command "Briefcase: Create DMG installer" \
        uv run briefcase package macOS --log
}

handler_show_app_location() {
    log_info "Project: $PROJECT_NAME (v$PROJECT_VERSION)"
    echo ""
    if [ -n "$APP_BUNDLE" ] && [ -d "$APP_BUNDLE" ]; then
        log_info "App bundle location:"
        echo "  $APP_BUNDLE"
        log_info "DMG location (if packaged):"
        DMG_FILE=$(find dist -name "${PROJECT_NAME}-*.dmg" 2>/dev/null | head -1)
        if [ -n "$DMG_FILE" ]; then
            echo "  $DMG_FILE"
        else
            echo "  (no DMG found in dist/)"
        fi
    else
        log_warn "App bundle not found. Build the app first (Briefcase menu option 3)."
        if [ -n "$APP_BUNDLE" ]; then
            log_info "Expected location: $APP_BUNDLE"
        fi
    fi
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

handler_sync_dependencies() {
    run_timed_command "Sync Python dependencies (uv sync --dev)" \
        uv sync --dev
    # Install package in editable mode so imports work in tests and development
    log_info "Installing package in editable mode..."
    uv pip install -e . >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        log_ok "Package installed in editable mode"
    else
        log_warning "Failed to install package in editable mode (this may be OK if already installed)"
    fi
}

# Briefcase submenu
briefcase_menu() {
    ui_run_page "Briefcase - Packaging Menu" \
        "1. Clean build artifacts"::handler_briefcase_clean \
        "2. Create app structure"::handler_briefcase_create \
        "3. Build the app"::handler_briefcase_build \
        "4. Test built .app"::handler_briefcase_test_app \
        "5. Dev mode (live reload)"::handler_briefcase_dev \
        "6. Create DMG installer"::handler_briefcase_package \
        "7. Show app/DMG locations"::handler_show_app_location \
        "8. View Briefcase logs"::handler_view_logs \
        "B. Back to main menu"::main_menu \
        "Q. Quit"::QUIT
}

handler_briefcase_menu() {
    briefcase_menu
}

# ============================================================================
# TYPE CHECKER HANDLERS
# ============================================================================

handler_mypy_check() {
    # Determine source directory to check
    local src_dir="src"
    if [ ! -d "$src_dir" ] && [ -d "${PROJECT_NAME//-/_}" ]; then
        src_dir="${PROJECT_NAME//-/_}"
    fi
    
    if command -v mypy >/dev/null 2>&1; then
        run_timed_command "mypy: Type checking" \
            mypy "$src_dir"
    else
        run_timed_command "mypy: Type checking" \
            uv run mypy "$src_dir"
    fi
}

handler_pyright_check() {
    # Determine source directory to check
    local src_dir="src"
    if [ ! -d "$src_dir" ] && [ -d "${PROJECT_NAME//-/_}" ]; then
        src_dir="${PROJECT_NAME//-/_}"
    fi
    
    if command -v pyright >/dev/null 2>&1; then
        run_timed_command "pyright: Type checking" \
            pyright "$src_dir"
    else
        run_timed_command "pyright: Type checking" \
            uv run pyright "$src_dir"
    fi
}

# ============================================================================
# TEST RUNNER HANDLERS
# ============================================================================

handler_pytest_run() {
    if command -v pytest >/dev/null 2>&1; then
        run_timed_command "pytest: Run tests" \
            pytest
    else
        run_timed_command "pytest: Run tests" \
            uv run pytest
    fi
}

handler_unittest_run() {
    # unittest uses Python's -m flag
    local test_dir="tests"
    if [ ! -d "$test_dir" ]; then
        test_dir="test"
    fi
    
    if [ -d "$test_dir" ]; then
        run_timed_command "unittest: Run tests" \
            uv run python -m unittest discover -s "$test_dir" -p "test_*.py"
    else
        run_timed_command "unittest: Run tests" \
            uv run python -m unittest discover -p "test_*.py"
    fi
}

handler_cleanup() {
    local cache_dirs="__pycache__, .ruff_cache, .pyright_cache, .pytest_cache, .mypy_cache"
    [ "$HAS_RUFF_CHECK" = true ] || cache_dirs=$(echo "$cache_dirs" | sed 's/, .ruff_cache//')
    [ "$HAS_PYRIGHT" = true ] || cache_dirs=$(echo "$cache_dirs" | sed 's/, .pyright_cache//')
    [ "$HAS_MYPY" = true ] || cache_dirs=$(echo "$cache_dirs" | sed 's/, .mypy_cache//')
    
    if confirm "This will clean $cache_dirs. Continue?"; then
        log_info "Cleaning cache directories..."
        find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
        [ "$HAS_RUFF_CHECK" = true ] && find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
        [ "$HAS_PYRIGHT" = true ] && find . -type d -name ".pyright_cache" -exec rm -r {} + 2>/dev/null || true
        [ "$HAS_MYPY" = true ] && find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
        find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        find . -type f -name "*.pyo" -delete 2>/dev/null || true
        log_ok "Cleanup completed"
    else
        log_info "Cleanup cancelled"
    fi
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

handler_show_env_info() {
    log_info "Environment Information:"
    echo ""
    echo "Project: $PROJECT_NAME (v$PROJECT_VERSION)"
    echo ""
    echo "Python version:"
    uv run python --version
    echo ""
    echo "Project location:"
    echo "  $SCRIPT_DIR"
    echo ""
    if [ -n "$ENTRY_POINT" ]; then
        echo "Entry point: $ENTRY_POINT"
        echo "Run command: $RUN_APP_CMD"
        echo ""
    fi
    echo "Installed packages:"
    uv pip list | head -20
    echo ""
    echo "(Showing first 20 packages, use 'uv pip list' for full list)"
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

handler_view_logs() {
    if [ -d "logs" ] && [ -n "$(ls -A logs 2>/dev/null)" ]; then
        log_info "Briefcase log files:"
        ls -lt logs/*.log 2>/dev/null | head -10 | awk '{print "  " $9 " (" $6 " " $7 " " $8 ")"}'
        echo ""
        LATEST_LOG=$(ls -t logs/*.log 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            if confirm "View latest log file: $LATEST_LOG?"; then
                less "$LATEST_LOG"
            fi
        fi
    else
        log_warn "No log files found in logs/ directory"
    fi
    echo ""
    printf "%bPress any key to continue...%b" "$COLOR_DIM" "$COLOR_RESET"
    read -n 1 -s
    echo ""
}

# ============================================================================
# MAIN MENU
# ============================================================================
# Dynamically builds menu based on detected tools and project configuration.
# Only shows menu items for tools that are actually available.
main_menu() {
    # Build dynamic menu title: "Dev Menu for Project: PROJECT-NAME vPROJECT-NUMBER (menu vMENU-NUMBER)"
    MENU_TITLE="Dev Menu for Project: $PROJECT_NAME"
    [ "$PROJECT_VERSION" != "unknown" ] && MENU_TITLE="$MENU_TITLE v$PROJECT_VERSION"
    MENU_TITLE="$MENU_TITLE (menu v${MENU_VERSION})"
    
    # Build menu items dynamically based on available tools
    local menu_items=()
    
    # Always available items
    menu_items+=("Run Python app (development)"::handler_run_python_app)
    
    # Dev mode (if scripts/dev.py exists)
    if [ -f "scripts/dev.py" ]; then
        menu_items+=("Dev mode: Live reload (watchdog)"::handler_dev_live_reload)
    fi
    
    # Qt Designer (if qt-designer.sh exists)
    if [ -f "qt-designer.sh" ]; then
        menu_items+=("Launch Qt Designer"::handler_qt_designer)
    fi
    
    # Build package (always available if uv is present)
    if [ "$HAS_UV" = true ]; then
        menu_items+=("Build Python package (wheel)"::handler_build_package)
    fi

    # Versioning (if script exists)
    if [ -f "scripts/bump-version.py" ]; then
        menu_items+=("Bump project version"::handler_bump_version)
    fi
    
    # Sync dependencies
    if [ "$HAS_UV" = true ]; then
        menu_items+=("Sync dependencies (uv sync --dev)"::handler_sync_dependencies)
    fi
    
    # Type checkers (show all available)
    if [ "$HAS_MYPY" = true ] && [ "$HAS_PYRIGHT" = true ]; then
        menu_items+=("mypy: Type checking"::handler_mypy_check)
        menu_items+=("pyright: Type checking"::handler_pyright_check)
    elif [ "$HAS_MYPY" = true ]; then
        menu_items+=("mypy: Type checking"::handler_mypy_check)
    elif [ "$HAS_PYRIGHT" = true ]; then
        menu_items+=("pyright: Type checking"::handler_pyright_check)
    fi
    
    # Test runners
    if [ "$HAS_PYTEST" = true ]; then
        menu_items+=("pytest: Run tests"::handler_pytest_run)
    fi
    if [ "$HAS_UNITTEST" = true ]; then
        menu_items+=("unittest: Run tests"::handler_unittest_run)
    fi
    
    # Cleanup (always available)
    menu_items+=("Cleanup cache directories"::handler_cleanup)
    
    # Environment info (always available)
    menu_items+=("Show environment info"::handler_show_env_info)
    
    # Linters
    if [ "$HAS_RUFF_CHECK" = true ]; then
        menu_items+=("Ruff: Check linting"::handler_ruff_check)
        menu_items+=("Ruff: Fix linting"::handler_ruff_fix)
    fi
    if [ "$HAS_FLAKE8" = true ]; then
        menu_items+=("flake8: Check linting"::handler_flake8_check)
    fi
    if [ "$HAS_PYLINT" = true ]; then
        menu_items+=("pylint: Check linting"::handler_pylint_check)
    fi
    
    # Formatters
    if [ "$HAS_RUFF_FORMAT" = true ]; then
        menu_items+=("Ruff: Check formatting"::handler_ruff_format_check)
        menu_items+=("Ruff: Fix formatting"::handler_ruff_format_fix)
    fi
    if [ "$HAS_BLACK" = true ]; then
        menu_items+=("black: Check formatting"::handler_black_check)
        menu_items+=("black: Fix formatting"::handler_black_fix)
    fi
    
    # Briefcase menu (if briefcase is available or likely used)
    if command -v briefcase >/dev/null 2>&1 || grep -qiE 'briefcase' pyproject.toml 2>/dev/null || [ -d "build" ]; then
        menu_items+=("Briefcase menu..."::handler_briefcase_menu)
    fi
    
    # Note: Quit option is automatically added by tui-menus.sh (fzf/gum/basic menu)
    
    # Build the ui_run_page command dynamically
    # Note: tui-menus.sh requires this format, so we need to call it with all items
    ui_run_page "$MENU_TITLE" "${menu_items[@]}"
}

# Run the main menu
main_menu
