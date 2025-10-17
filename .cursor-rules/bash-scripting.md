# Bash Scripting Standards

## Script Template

### Basic Template
```bash
#!/usr/bin/env bash
#
# Script: script_name.sh
# Description: Brief description of what this script does
# Author: Your Name
# Date: 2025-01-17
#
# Usage: ./script_name.sh [options]
#

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'        # Set Internal Field Separator to newline and tab

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly LOG_FILE="${LOG_FILE:-/tmp/${SCRIPT_NAME}.log}"

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
DRY_RUN=false
VERBOSE=false

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

# Print error message and exit
error_exit() {
    echo "ERROR: $1" >&2
    exit "${2:-1}"
}

# Print warning message
warn() {
    echo "WARNING: $1" >&2
}

# Print info message
info() {
    echo "INFO: $1"
}

# Print debug message if verbose
debug() {
    if [[ "${VERBOSE}" == "true" ]]; then
        echo "DEBUG: $1" >&2
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Description of what the script does.

OPTIONS:
    -h, --help          Display this help message
    -v, --verbose       Enable verbose output
    -d, --dry-run       Dry run mode (no changes)
    -f, --file FILE     Input file (required)
    -o, --output DIR    Output directory (default: current directory)

EXAMPLES:
    ${SCRIPT_NAME} -f input.txt
    ${SCRIPT_NAME} -f input.txt -o /tmp/output -v

EOF
    exit 0
}

# Cleanup function
cleanup() {
    local exit_code=$?
    debug "Cleaning up..."
    # Add cleanup tasks here
    exit "${exit_code}"
}

# Validate requirements
validate_requirements() {
    local required_commands=("jq" "curl" "awk")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "${cmd}" &> /dev/null; then
            error_exit "Required command not found: ${cmd}"
        fi
    done
    
    debug "All required commands are available"
}

# Main function
main() {
    local input_file=""
    local output_dir="."
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--file)
                input_file="$2"
                shift 2
                ;;
            -o|--output)
                output_dir="$2"
                shift 2
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done
    
    # Validate required arguments
    if [[ -z "${input_file}" ]]; then
        error_exit "Input file is required. Use -f or --file option."
    fi
    
    if [[ ! -f "${input_file}" ]]; then
        error_exit "Input file not found: ${input_file}"
    fi
    
    # Validate requirements
    validate_requirements
    
    # Main logic here
    info "Processing ${input_file}..."
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        info "DRY RUN: Would process file"
    else
        # Actual processing
        debug "Performing actual processing"
    fi
    
    info "Processing complete"
}

# -----------------------------------------------------------------------------
# Script Entry Point
# -----------------------------------------------------------------------------

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Run main function
main "$@"
```

## Best Practices

### Error Handling
```bash
# Always use set -e to exit on errors
set -euo pipefail

# Check command success explicitly when needed
if ! command_that_might_fail; then
    error_exit "Command failed"
fi

# Use conditional execution
mkdir -p /tmp/mydir || error_exit "Failed to create directory"

# Handle pipeline errors
if ! cat file.txt | grep pattern | wc -l > /dev/null; then
    error_exit "Pipeline failed"
fi
```

### Input Validation
```bash
validate_input() {
    local input="$1"
    
    # Check if empty
    if [[ -z "${input}" ]]; then
        error_exit "Input cannot be empty"
    fi
    
    # Check if file exists
    if [[ ! -f "${input}" ]]; then
        error_exit "File not found: ${input}"
    fi
    
    # Check if directory exists
    if [[ ! -d "${input}" ]]; then
        error_exit "Directory not found: ${input}"
    fi
    
    # Check if readable
    if [[ ! -r "${input}" ]]; then
        error_exit "File not readable: ${input}"
    fi
    
    # Check if writable
    if [[ ! -w "${input}" ]]; then
        error_exit "File not writable: ${input}"
    fi
    
    # Check if executable
    if [[ ! -x "${input}" ]]; then
        error_exit "File not executable: ${input}"
    fi
    
    # Validate format with regex
    if [[ ! "${input}" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        error_exit "Invalid format: ${input}"
    fi
}
```

### Variable Naming
```bash
# Constants (readonly)
readonly MAX_RETRIES=3
readonly API_URL="https://api.example.com"

# Local variables in functions
local_function() {
    local temp_var="value"
    local count=0
}

# Environment variables (UPPER_CASE)
export DATABASE_URL="postgres://localhost/db"
export LOG_LEVEL="info"

# Regular variables (lowercase with underscores)
input_file="/path/to/file"
retry_count=0
```

### Arrays
```bash
# Declare array
declare -a files=("file1.txt" "file2.txt" "file3.txt")

# Add to array
files+=("file4.txt")

# Iterate over array
for file in "${files[@]}"; do
    info "Processing ${file}"
done

# Array length
echo "Total files: ${#files[@]}"

# Check if value exists in array
if [[ " ${files[*]} " =~ " file1.txt " ]]; then
    info "file1.txt exists in array"
fi

# Associative arrays (like dictionaries)
declare -A config=(
    ["host"]="localhost"
    ["port"]="5432"
    ["user"]="admin"
)

# Access associative array
echo "Host: ${config[host]}"

# Iterate over associative array
for key in "${!config[@]}"; do
    echo "${key}: ${config[$key]}"
done
```

### Loops
```bash
# For loop with range
for i in {1..10}; do
    echo "Iteration ${i}"
done

# For loop with command output
for file in $(find . -name "*.txt"); do
    process_file "${file}"
done

# While loop
count=0
while [[ ${count} -lt 10 ]]; do
    echo "Count: ${count}"
    ((count++))
done

# Read file line by line
while IFS= read -r line; do
    echo "Line: ${line}"
done < input.txt

# Until loop
until [[ -f /tmp/ready ]]; do
    echo "Waiting..."
    sleep 1
done
```

### Conditionals
```bash
# If statement
if [[ -f "/path/to/file" ]]; then
    info "File exists"
elif [[ -d "/path/to/file" ]]; then
    info "Directory exists"
else
    warn "Path does not exist"
fi

# String comparison
if [[ "${var}" == "value" ]]; then
    info "Match"
fi

# Numeric comparison
if [[ ${count} -gt 10 ]]; then
    info "Greater than 10"
fi

# Multiple conditions
if [[ -f "${file}" && -r "${file}" ]]; then
    info "File exists and is readable"
fi

# Negation
if [[ ! -f "${file}" ]]; then
    warn "File does not exist"
fi

# Case statement
case "${option}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        start_service
        ;;
    *)
        error_exit "Unknown option: ${option}"
        ;;
esac
```

### Functions
```bash
# Function with parameters
process_file() {
    local input_file="$1"
    local output_file="$2"
    
    if [[ ! -f "${input_file}" ]]; then
        error_exit "Input file not found: ${input_file}"
    fi
    
    # Process file
    cat "${input_file}" | grep pattern > "${output_file}"
    
    return 0
}

# Function with return value
get_file_count() {
    local directory="$1"
    local count
    
    count=$(find "${directory}" -type f | wc -l)
    echo "${count}"
}

# Usage
file_count=$(get_file_count "/tmp")
info "File count: ${file_count}"
```

### String Operations
```bash
# String length
text="hello world"
echo "Length: ${#text}"

# Substring
echo "Substring: ${text:0:5}"  # "hello"

# Replace
echo "Replace: ${text/world/universe}"  # "hello universe"

# Replace all
text="foo bar foo"
echo "Replace all: ${text//foo/baz}"  # "baz bar baz"

# Remove prefix
filename="/path/to/file.txt"
echo "Basename: ${filename##*/}"  # "file.txt"

# Remove suffix
echo "Without extension: ${filename%.txt}"  # "/path/to/file"

# Uppercase
echo "Uppercase: ${text^^}"

# Lowercase
echo "Lowercase: ${text,,}"

# Default value
echo "Value: ${UNDEFINED_VAR:-default}"

# Trim whitespace
trim() {
    local var="$1"
    var="${var#"${var%%[![:space:]]*}"}"  # Trim leading
    var="${var%"${var##*[![:space:]]}"}"  # Trim trailing
    echo "${var}"
}
```

### Date and Time
```bash
# Current date and time
now=$(date +"%Y-%m-%d %H:%M:%S")
echo "Current time: ${now}"

# Timestamp
timestamp=$(date +%s)
echo "Timestamp: ${timestamp}"

# Formatted date
date_str=$(date +"%Y%m%d")
echo "Date string: ${date_str}"

# Date arithmetic (requires GNU date)
yesterday=$(date -d "yesterday" +"%Y-%m-%d")
next_week=$(date -d "+7 days" +"%Y-%m-%d")
```

### File Operations
```bash
# Create directory
mkdir -p /path/to/directory

# Remove directory
rm -rf /path/to/directory

# Copy files
cp source.txt destination.txt
cp -r source_dir/ destination_dir/

# Move/rename
mv old_name.txt new_name.txt

# Check file age
file_age_seconds=$(($(date +%s) - $(stat -f %m "${file}")))

# Create temporary file
temp_file=$(mktemp)
echo "Temporary file: ${temp_file}"

# Create temporary directory
temp_dir=$(mktemp -d)
echo "Temporary directory: ${temp_dir}"
```

### Process Management
```bash
# Run command in background
long_running_command &
bg_pid=$!

# Wait for background process
wait ${bg_pid}

# Kill process
kill ${bg_pid}

# Check if process is running
if ps -p ${bg_pid} > /dev/null; then
    echo "Process is running"
fi

# Parallel execution
for file in *.txt; do
    process_file "${file}" &
done
wait  # Wait for all background jobs
```

### Logging
```bash
# Setup logging
setup_logging() {
    local log_dir="$(dirname "${LOG_FILE}")"
    mkdir -p "${log_dir}"
    
    # Redirect all output to log file
    exec 1> >(tee -a "${LOG_FILE}")
    exec 2>&1
}

# Log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# Usage
log "INFO: Starting process"
log "ERROR: Process failed"
```

### Command Availability Check
```bash
# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Usage
if command_exists docker; then
    info "Docker is installed"
else
    error_exit "Docker is not installed"
fi

# Check multiple commands
check_requirements() {
    local missing=()
    
    for cmd in "$@"; do
        if ! command_exists "${cmd}"; then
            missing+=("${cmd}")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        error_exit "Missing required commands: ${missing[*]}"
    fi
}

# Usage
check_requirements git docker kubectl
```

## Security Best Practices

```bash
# Use quotes around variables
rm -rf "${directory}"  # Good
rm -rf $directory      # Bad - can cause issues with spaces

# Avoid eval
# Bad:
eval "rm -rf ${dir}"

# Good:
rm -rf "${dir}"

# Validate user input
sanitize_input() {
    local input="$1"
    # Remove dangerous characters
    echo "${input}" | tr -cd '[:alnum:]._-'
}

# Use temporary files securely
temp_file=$(mktemp)
chmod 600 "${temp_file}"  # Restrict permissions

# Don't expose secrets in process list
# Bad:
mysql -u user -pPASSWORD

# Good:
mysql --defaults-extra-file=<(echo -e "[client]\npassword=PASSWORD")
```

## Checklist

- ✅ Shebang: `#!/usr/bin/env bash`
- ✅ Safe mode: `set -euo pipefail`
- ✅ Usage function with examples
- ✅ Input validation
- ✅ Error handling with meaningful messages
- ✅ Logging with timestamps
- ✅ Cleanup with trap
- ✅ Check command availability
- ✅ Use readonly for constants
- ✅ Use local for function variables
- ✅ Quote all variables
- ✅ Meaningful variable and function names
- ✅ Comments for complex logic

