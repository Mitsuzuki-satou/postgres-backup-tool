#!/bin/bash

# =============================================================================
# PostgreSQL Advanced Backup and Restore Tool
# Version: 2.0
# Author: Enhanced by AI Assistant
# Description: User-friendly PostgreSQL backup and restore with visual feedback
# =============================================================================

set -euo pipefail  # Enhanced error handling

# Color definitions for better visualization
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Unicode symbols for better UX
readonly CHECK="✓"
readonly CROSS="✗"
readonly ARROW="→"
readonly GEAR="⚙"
readonly DATABASE="🗄"
readonly BACKUP="💾"
readonly RESTORE="📥"
readonly CLOCK="⏱"

# Configuration file path
readonly CONFIG_FILE="$HOME/.postgres_backup_config"
readonly LOG_DIR="$HOME/.postgres_backup_logs"
readonly LOG_FILE="$LOG_DIR/backup_restore_$(date +%Y%m%d_%H%M%S).log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print section header
print_header() {
    local title=$1
    local width=80
    local padding=$(( (width - ${#title} - 2) / 2 ))
    
    echo
    print_color "$CYAN" "$(printf '=%.0s' $(seq 1 $width))"
    print_color "$WHITE" "$(printf '%*s %s %*s' $padding '' "$title" $padding '')"
    print_color "$CYAN" "$(printf '=%.0s' $(seq 1 $width))"
    echo
}

# Print step header
print_step() {
    local step_num=$1
    local step_desc=$2
    echo
    print_color "$BLUE" "${BOLD}STEP $step_num: $step_desc${NC}"
    print_color "$BLUE" "$(printf '─%.0s' $(seq 1 50))"
}

# Progress bar function
show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local width=50
    local percentage=$((current * 100 / total))
    local completed=$((current * width / total))
    local remaining=$((width - completed))
    
    printf "\r${CYAN}${message} [${GREEN}$(printf '█%.0s' $(seq 1 $completed))${WHITE}$(printf '░%.0s' $(seq 1 $remaining))${CYAN}] ${percentage}%% ${NC}"
}

# Enhanced progress tracking for database operations
track_progress() {
    local operation=$1
    local pid=$2
    local estimated_time=${3:-60}  # Default 60 seconds
    local message=$4
    
    local start_time=$(date +%s)
    local elapsed=0
    local progress=0
    
    while kill -0 $pid 2>/dev/null; do
        elapsed=$(($(date +%s) - start_time))
        
        # Calculate progress based on elapsed time vs estimated time
        if [[ $elapsed -lt $estimated_time ]]; then
            progress=$((elapsed * 100 / estimated_time))
        else
            # If operation takes longer than expected, show 95% to indicate it's still running
            progress=95
        fi
        
        # Ensure progress doesn't exceed 99% while process is running
        if [[ $progress -gt 99 ]]; then
            progress=99
        fi
        
        show_progress $progress 100 "$message"
        
        # Show additional info
        local mins=$((elapsed / 60))
        local secs=$((elapsed % 60))
        printf "${YELLOW} [${mins}m${secs}s elapsed]${NC}"
        
        sleep 1
    done
    
    # Show completion
    show_progress 100 100 "$message"
    printf "${GREEN} [Completed in ${mins}m${secs}s]${NC}\n"
    echo
}

# Monitor file size growth for backup progress
monitor_backup_progress() {
    local backup_file=$1
    local pid=$2
    local message=$3
    local target_size_mb=${4:-100}  # Estimated target size in MB
    
    local start_time=$(date +%s)
    local last_size=0
    local current_size=0
    local speed=0
    
    while kill -0 $pid 2>/dev/null; do
        if [[ -f "$backup_file" ]]; then
            current_size=$(du -m "$backup_file" 2>/dev/null | cut -f1 || echo "0")
            
            # Calculate progress percentage
            local progress=$((current_size * 100 / target_size_mb))
            if [[ $progress -gt 99 ]]; then
                progress=99
            fi
            
            # Calculate speed
            local elapsed=$(($(date +%s) - start_time))
            if [[ $elapsed -gt 0 ]]; then
                speed=$((current_size / elapsed))
            fi
            
            show_progress $progress 100 "$message"
            printf "${YELLOW} [${current_size}MB @ ${speed}MB/s]${NC}"
            
            last_size=$current_size
        else
            # File doesn't exist yet, show initialization
            printf "\r${CYAN}${message} ${YELLOW}[Initializing...]${NC}"
        fi
        
        sleep 1
    done
    
    # Final size and completion
    if [[ -f "$backup_file" ]]; then
        current_size=$(du -m "$backup_file" 2>/dev/null | cut -f1 || echo "0")
    fi
    
    show_progress 100 100 "$message"
    printf "${GREEN} [${current_size}MB completed]${NC}\n"
    echo
}

# Monitor table restoration progress
monitor_restore_progress() {
    local database=$1
    local pid=$2
    local message=$3
    local estimated_tables=${4:-50}  # Estimated number of tables
    
    local start_time=$(date +%s)
    
    while kill -0 $pid 2>/dev/null; do
        # Count current tables in the database
        export PGPASSWORD="${CONFIG[LOCAL_PASSWORD]}"
        local current_tables=$(psql -h "${CONFIG[LOCAL_HOST]}" -p "${CONFIG[LOCAL_PORT]}" -U "${CONFIG[LOCAL_USER]}" -d "$database" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
        
        # Calculate progress
        local progress=0
        if [[ $estimated_tables -gt 0 && $current_tables -gt 0 ]]; then
            progress=$((current_tables * 100 / estimated_tables))
            if [[ $progress -gt 99 ]]; then
                progress=99
            fi
        else
            # Fallback to time-based progress
            local elapsed=$(($(date +%s) - start_time))
            progress=$((elapsed * 100 / 120))  # Assume 2 minutes max
            if [[ $progress -gt 99 ]]; then
                progress=99
            fi
        fi
        
        show_progress $progress 100 "$message"
        printf "${YELLOW} [${current_tables} tables restored]${NC}"
        
        sleep 2
    done
    
    # Final count
    export PGPASSWORD="${CONFIG[LOCAL_PASSWORD]}"
    local final_tables=$(psql -h "${CONFIG[LOCAL_HOST]}" -p "${CONFIG[LOCAL_PORT]}" -U "${CONFIG[LOCAL_USER]}" -d "$database" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
    
    show_progress 100 100 "$message"
    printf "${GREEN} [${final_tables} tables completed]${NC}\n"
    echo
}

# Spinner for long operations
spinner() {
    local pid=$1
    local message=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    
    while kill -0 $pid 2>/dev/null; do
        printf "\r${YELLOW}${spin:$i:1} $message${NC}"
        i=$(( (i+1) %10 ))
        sleep 0.1
    done
    printf "\r"
}

# Error handling
handle_error() {
    local exit_code=$1
    local line_number=$2
    print_color "$RED" "${CROSS} ERROR: Command failed at line $line_number with exit code $exit_code"
    log "ERROR: Script failed at line $line_number with exit code $exit_code"
    cleanup_on_error
    exit $exit_code
}

# Cleanup on error
cleanup_on_error() {
    if [[ -n "${BACKUP_FILE:-}" && -f "$BACKUP_FILE" ]]; then
        print_color "$YELLOW" "Cleaning up incomplete backup file..."
        rm -f "$BACKUP_FILE"
    fi
}

# Trap errors
trap 'handle_error $? $LINENO' ERR

# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

# Default configuration
declare -A CONFIG=(
    [REMOTE_HOST]="46.250.224.248"
    [REMOTE_PORT]="54321"
    [REMOTE_DB]="dccpadmin_backup1"
    [REMOTE_USER]="philex"
    [REMOTE_PASSWORD]="admin@123"
    [LOCAL_HOST]="localhost"
    [LOCAL_PORT]="5432"
    [LOCAL_USER]="postgres"
    [LOCAL_PASSWORD]="postgres"
    [NEW_DB_NAME]="dccpadmin_backup_restored"
    [BACKUP_DIR]="$HOME/postgres_backups"
    [COMPRESSION]="true"
    [PARALLEL_JOBS]="4"
)

# Load configuration from file
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        print_color "$GREEN" "${CHECK} Loading configuration from $CONFIG_FILE"
        source "$CONFIG_FILE"
        
        # Update CONFIG array with loaded values
        [[ -n "${REMOTE_HOST:-}" ]] && CONFIG[REMOTE_HOST]="$REMOTE_HOST"
        [[ -n "${REMOTE_PORT:-}" ]] && CONFIG[REMOTE_PORT]="$REMOTE_PORT"
        [[ -n "${REMOTE_DB:-}" ]] && CONFIG[REMOTE_DB]="$REMOTE_DB"
        [[ -n "${REMOTE_USER:-}" ]] && CONFIG[REMOTE_USER]="$REMOTE_USER"
        [[ -n "${REMOTE_PASSWORD:-}" ]] && CONFIG[REMOTE_PASSWORD]="$REMOTE_PASSWORD"
        [[ -n "${LOCAL_HOST:-}" ]] && CONFIG[LOCAL_HOST]="$LOCAL_HOST"
        [[ -n "${LOCAL_PORT:-}" ]] && CONFIG[LOCAL_PORT]="$LOCAL_PORT"
        [[ -n "${LOCAL_USER:-}" ]] && CONFIG[LOCAL_USER]="$LOCAL_USER"
        [[ -n "${LOCAL_PASSWORD:-}" ]] && CONFIG[LOCAL_PASSWORD]="$LOCAL_PASSWORD"
        [[ -n "${NEW_DB_NAME:-}" ]] && CONFIG[NEW_DB_NAME]="$NEW_DB_NAME"
        [[ -n "${BACKUP_DIR:-}" ]] && CONFIG[BACKUP_DIR]="$BACKUP_DIR"
        [[ -n "${COMPRESSION:-}" ]] && CONFIG[COMPRESSION]="$COMPRESSION"
        [[ -n "${PARALLEL_JOBS:-}" ]] && CONFIG[PARALLEL_JOBS]="$PARALLEL_JOBS"
    else
        print_color "$YELLOW" "${GEAR} No configuration file found, using defaults"
    fi
}

# Save configuration to file
save_config() {
    print_color "$BLUE" "Saving configuration to $CONFIG_FILE..."
    cat > "$CONFIG_FILE" << EOF
# PostgreSQL Backup & Restore Configuration
# Generated on $(date)

# Remote Database Configuration
REMOTE_HOST="${CONFIG[REMOTE_HOST]}"
REMOTE_PORT="${CONFIG[REMOTE_PORT]}"
REMOTE_DB="${CONFIG[REMOTE_DB]}"
REMOTE_USER="${CONFIG[REMOTE_USER]}"
REMOTE_PASSWORD="${CONFIG[REMOTE_PASSWORD]}"

# Local Database Configuration
LOCAL_HOST="${CONFIG[LOCAL_HOST]}"
LOCAL_PORT="${CONFIG[LOCAL_PORT]}"
LOCAL_USER="${CONFIG[LOCAL_USER]}"
LOCAL_PASSWORD="${CONFIG[LOCAL_PASSWORD]}"
NEW_DB_NAME="${CONFIG[NEW_DB_NAME]}"

# Backup Configuration
BACKUP_DIR="${CONFIG[BACKUP_DIR]}"
COMPRESSION="${CONFIG[COMPRESSION]}"
PARALLEL_JOBS="${CONFIG[PARALLEL_JOBS]}"
EOF
    print_color "$GREEN" "${CHECK} Configuration saved successfully!"
}

# Interactive configuration
configure_interactive() {
    print_header "INTERACTIVE CONFIGURATION"
    
    echo "Current configuration:"
    echo
    printf "%-20s: %s\n" "Remote Host" "${CONFIG[REMOTE_HOST]}"
    printf "%-20s: %s\n" "Remote Port" "${CONFIG[REMOTE_PORT]}"
    printf "%-20s: %s\n" "Remote Database" "${CONFIG[REMOTE_DB]}"
    printf "%-20s: %s\n" "Remote User" "${CONFIG[REMOTE_USER]}"
    printf "%-20s: %s\n" "Local Host" "${CONFIG[LOCAL_HOST]}"
    printf "%-20s: %s\n" "Local Port" "${CONFIG[LOCAL_PORT]}"
    printf "%-20s: %s\n" "Local User" "${CONFIG[LOCAL_USER]}"
    printf "%-20s: %s\n" "New Database Name" "${CONFIG[NEW_DB_NAME]}"
    printf "%-20s: %s\n" "Backup Directory" "${CONFIG[BACKUP_DIR]}"
    printf "%-20s: %s\n" "Compression" "${CONFIG[COMPRESSION]}"
    printf "%-20s: %s\n" "Parallel Jobs" "${CONFIG[PARALLEL_JOBS]}"
    echo
    
    read -p "Do you want to modify the configuration? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Remote Host [${CONFIG[REMOTE_HOST]}]: " input
        [[ -n "$input" ]] && CONFIG[REMOTE_HOST]="$input"
        
        read -p "Remote Port [${CONFIG[REMOTE_PORT]}]: " input
        [[ -n "$input" ]] && CONFIG[REMOTE_PORT]="$input"
        
        read -p "Remote Database [${CONFIG[REMOTE_DB]}]: " input
        [[ -n "$input" ]] && CONFIG[REMOTE_DB]="$input"
        
        read -p "Remote User [${CONFIG[REMOTE_USER]}]: " input
        [[ -n "$input" ]] && CONFIG[REMOTE_USER]="$input"
        
        read -s -p "Remote Password: " input
        echo
        [[ -n "$input" ]] && CONFIG[REMOTE_PASSWORD]="$input"
        
        read -p "Local Host [${CONFIG[LOCAL_HOST]}]: " input
        [[ -n "$input" ]] && CONFIG[LOCAL_HOST]="$input"
        
        read -p "Local Port [${CONFIG[LOCAL_PORT]}]: " input
        [[ -n "$input" ]] && CONFIG[LOCAL_PORT]="$input"
        
        read -p "Local User [${CONFIG[LOCAL_USER]}]: " input
        [[ -n "$input" ]] && CONFIG[LOCAL_USER]="$input"
        
        read -s -p "Local Password: " input
        echo
        [[ -n "$input" ]] && CONFIG[LOCAL_PASSWORD]="$input"
        
        read -p "New Database Name [${CONFIG[NEW_DB_NAME]}]: " input
        [[ -n "$input" ]] && CONFIG[NEW_DB_NAME]="$input"
        
        read -p "Backup Directory [${CONFIG[BACKUP_DIR]}]: " input
        [[ -n "$input" ]] && CONFIG[BACKUP_DIR]="$input"
        
        read -p "Enable Compression (true/false) [${CONFIG[COMPRESSION]}]: " input
        [[ -n "$input" ]] && CONFIG[COMPRESSION]="$input"
        
        read -p "Parallel Jobs [${CONFIG[PARALLEL_JOBS]}]: " input
        [[ -n "$input" ]] && CONFIG[PARALLEL_JOBS]="$input"
        
        save_config
    fi
}

# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

# Test database connection
test_connection() {
    local host=$1
    local port=$2
    local user=$3
    local password=$4
    local database=${5:-"postgres"}
    local desc=$6
    
    print_color "$YELLOW" "${GEAR} Testing $desc connection..."
    
    export PGPASSWORD="$password"
    if psql -h "$host" -p "$port" -U "$user" -d "$database" -c "SELECT version();" &>/dev/null; then
        print_color "$GREEN" "${CHECK} $desc connection successful"
        return 0
    else
        print_color "$RED" "${CROSS} $desc connection failed"
        return 1
    fi
}

# Get database size
get_db_size() {
    local host=$1
    local port=$2
    local user=$3
    local password=$4
    local database=$5
    
    export PGPASSWORD="$password"
    local size=$(psql -h "$host" -p "$port" -U "$user" -d "$database" -tAc "SELECT pg_size_pretty(pg_database_size('$database'));")
    echo "$size"
}

# Get table count
get_table_count() {
    local host=$1
    local port=$2
    local user=$3
    local password=$4
    local database=$5
    
    export PGPASSWORD="$password"
    local count=$(psql -h "$host" -p "$port" -U "$user" -d "$database" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    echo "$count"
}

# Create backup
create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="${CONFIG[REMOTE_DB]}_${timestamp}"
    
    # Create backup directory
    mkdir -p "${CONFIG[BACKUP_DIR]}"
    
    export PGPASSWORD="${CONFIG[REMOTE_PASSWORD]}"
    
    print_color "$BLUE" "${BACKUP} Starting backup process..."
    print_color "$CYAN" "Source: ${CONFIG[REMOTE_HOST]}:${CONFIG[REMOTE_PORT]}/${CONFIG[REMOTE_DB]}"
    
    # Get source database size for progress estimation
    local source_size_pretty=$(get_db_size "${CONFIG[REMOTE_HOST]}" "${CONFIG[REMOTE_PORT]}" "${CONFIG[REMOTE_USER]}" "${CONFIG[REMOTE_PASSWORD]}" "${CONFIG[REMOTE_DB]}")
    local source_size_mb=$(psql -h "${CONFIG[REMOTE_HOST]}" -p "${CONFIG[REMOTE_PORT]}" -U "${CONFIG[REMOTE_USER]}" -d "${CONFIG[REMOTE_DB]}" -tAc "SELECT ROUND(pg_database_size('${CONFIG[REMOTE_DB]}') / 1024.0 / 1024.0);" 2>/dev/null || echo "100")
    
    print_color "$YELLOW" "Database size: $source_size_pretty (estimating ${source_size_mb}MB backup)"
    echo
    
    # Check if we should use directory format for parallel processing
    if [[ "${CONFIG[PARALLEL_JOBS]}" -gt 1 && "${CONFIG[COMPRESSION]}" == "true" ]]; then
        # Use directory format with parallel jobs and compression
        local backup_dir="${CONFIG[BACKUP_DIR]}/${backup_name}_dir"
        BACKUP_FILE="${CONFIG[BACKUP_DIR]}/${backup_name}.tar.gz"
        
        print_color "$CYAN" "Target: $backup_dir (will be compressed to $(basename "$BACKUP_FILE"))"
        echo
        
        # Create backup using directory format with parallel jobs
        pg_dump -h "${CONFIG[REMOTE_HOST]}" -p "${CONFIG[REMOTE_PORT]}" -U "${CONFIG[REMOTE_USER]}" -d "${CONFIG[REMOTE_DB]}" \
            --verbose --clean --no-owner --no-privileges \
            --format=directory --jobs=${CONFIG[PARALLEL_JOBS]} \
            --file="$backup_dir" &>/dev/null &
        
        local pid=$!
        track_progress "parallel_backup" $pid 90 "Creating parallel backup"
        wait $pid
        
        if [[ $? -eq 0 ]]; then
            print_color "$YELLOW" "${GEAR} Compressing backup directory..."
            tar -czf "$BACKUP_FILE" -C "${CONFIG[BACKUP_DIR]}" "$(basename "$backup_dir")" &
            local compress_pid=$!
            track_progress "compression" $compress_pid 30 "Compressing backup"
            wait $compress_pid
            
            # Remove the directory after compression
            rm -rf "$backup_dir"
        else
            print_color "$RED" "${CROSS} Backup failed!"
            return 1
        fi
        
    elif [[ "${CONFIG[COMPRESSION]}" == "true" ]]; then
        # Use SQL format with compression (no parallel jobs)
        BACKUP_FILE="${CONFIG[BACKUP_DIR]}/${backup_name}.sql.gz"
        print_color "$CYAN" "Target: $BACKUP_FILE"
        echo
        
        pg_dump -h "${CONFIG[REMOTE_HOST]}" -p "${CONFIG[REMOTE_PORT]}" -U "${CONFIG[REMOTE_USER]}" -d "${CONFIG[REMOTE_DB]}" \
            --verbose --clean --no-owner --no-privileges | gzip > "$BACKUP_FILE" &
        
        local pid=$!
        # Estimate compressed size as 30% of original
        local estimated_size=$((source_size_mb * 30 / 100))
        monitor_backup_progress "$BACKUP_FILE" $pid "Creating compressed backup" $estimated_size
        wait $pid
        
    else
        # Use regular SQL format (no compression, no parallel jobs)
        BACKUP_FILE="${CONFIG[BACKUP_DIR]}/${backup_name}.sql"
        print_color "$CYAN" "Target: $BACKUP_FILE"
        echo
        
        pg_dump -h "${CONFIG[REMOTE_HOST]}" -p "${CONFIG[REMOTE_PORT]}" -U "${CONFIG[REMOTE_USER]}" -d "${CONFIG[REMOTE_DB]}" \
            --verbose --clean --no-owner --no-privileges > "$BACKUP_FILE" &
        
        local pid=$!
        # Estimate uncompressed SQL size as 80% of database size
        local estimated_size=$((source_size_mb * 80 / 100))
        monitor_backup_progress "$BACKUP_FILE" $pid "Creating backup" $estimated_size
        wait $pid
    fi
    
    if [[ $? -eq 0 ]]; then
        local file_size=$(du -h "$BACKUP_FILE" | cut -f1)
        print_color "$GREEN" "${CHECK} Backup created successfully!"
        print_color "$GREEN" "   File: $(basename "$BACKUP_FILE")"
        print_color "$GREEN" "   Size: $file_size"
        print_color "$GREEN" "   Location: $BACKUP_FILE"
        log "Backup created: $BACKUP_FILE ($file_size)"
        return 0
    else
        print_color "$RED" "${CROSS} Backup failed!"
        return 1
    fi
}

# Restore backup
restore_backup() {
    print_color "$BLUE" "${RESTORE} Starting restore process..."
    
    # Check if database exists and handle accordingly
    export PGPASSWORD="${CONFIG[LOCAL_PASSWORD]}"
    local db_exists=$(psql -h "${CONFIG[LOCAL_HOST]}" -p "${CONFIG[LOCAL_PORT]}" -U "${CONFIG[LOCAL_USER]}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${CONFIG[NEW_DB_NAME]}'" 2>/dev/null || echo "0")
    
    if [[ "$db_exists" == "1" ]]; then
        print_color "$YELLOW" "⚠ Database '${CONFIG[NEW_DB_NAME]}' already exists!"
        echo
        print_color "$CYAN" "Options:"
        print_color "$CYAN" "  1) Drop and recreate (DESTRUCTIVE)"
        print_color "$CYAN" "  2) Use different name"
        print_color "$CYAN" "  3) Cancel operation"
        echo
        
        while true; do
            read -p "Select option (1-3): " choice
            case $choice in
                1)
                    print_color "$YELLOW" "Dropping existing database..."
                    psql -h "${CONFIG[LOCAL_HOST]}" -p "${CONFIG[LOCAL_PORT]}" -U "${CONFIG[LOCAL_USER]}" -d postgres -c "DROP DATABASE \"${CONFIG[NEW_DB_NAME]}\";" &>/dev/null
                    break
                    ;;
                2)
                    read -p "Enter new database name: " new_name
                    [[ -n "$new_name" ]] && CONFIG[NEW_DB_NAME]="$new_name" && break
                    ;;
                3)
                    print_color "$YELLOW" "Operation cancelled"
                    return 1
                    ;;
                *)
                    print_color "$RED" "Invalid option. Please select 1, 2, or 3."
                    ;;
            esac
        done
    fi
    
    # Create database
    print_color "$BLUE" "${DATABASE} Creating database '${CONFIG[NEW_DB_NAME]}'..."
    psql -h "${CONFIG[LOCAL_HOST]}" -p "${CONFIG[LOCAL_PORT]}" -U "${CONFIG[LOCAL_USER]}" -d postgres -c "CREATE DATABASE \"${CONFIG[NEW_DB_NAME]}\";" &>/dev/null
    
    # Restore from backup
    print_color "$BLUE" "${RESTORE} Restoring data to '${CONFIG[NEW_DB_NAME]}'..."
    
    # Get source table count for progress estimation
    local source_table_count=50  # Default estimate
    if [[ "$BACKUP_FILE" == *.sql || "$BACKUP_FILE" == *.sql.gz ]]; then
        # Try to count CREATE TABLE statements in SQL backup
        if [[ "$BACKUP_FILE" == *.sql.gz ]]; then
            source_table_count=$(zcat "$BACKUP_FILE" | grep -c "CREATE TABLE" 2>/dev/null || echo "50")
        else
            source_table_count=$(grep -c "CREATE TABLE" "$BACKUP_FILE" 2>/dev/null || echo "50")
        fi
    fi
    
    print_color "$YELLOW" "Estimated tables to restore: $source_table_count"
    echo
    
    if [[ "$BACKUP_FILE" == *.tar.gz ]]; then
        # Handle directory format backup (compressed tar)
        local temp_dir=$(mktemp -d)
        print_color "$YELLOW" "${GEAR} Extracting backup archive..."
        tar -xzf "$BACKUP_FILE" -C "$temp_dir" &
        local extract_pid=$!
        track_progress "extraction" $extract_pid 20 "Extracting backup archive"
        wait $extract_pid
        
        # Find the extracted directory
        local backup_dir=$(find "$temp_dir" -type d -name "*_dir" | head -1)
        if [[ -z "$backup_dir" ]]; then
            backup_dir=$(find "$temp_dir" -mindepth 1 -maxdepth 1 -type d | head -1)
        fi
        
        # Get table count from directory backup TOC
        local toc_file="$backup_dir/toc.dat"
        if [[ -f "$toc_file" ]]; then
            source_table_count=$(grep -c "TABLE" "$toc_file" 2>/dev/null || echo "$source_table_count")
        fi
        
        print_color "$BLUE" "Starting parallel restore with ${CONFIG[PARALLEL_JOBS]} jobs..."
        
        # Restore using pg_restore for directory format
        pg_restore -h "${CONFIG[LOCAL_HOST]}" -p "${CONFIG[LOCAL_PORT]}" -U "${CONFIG[LOCAL_USER]}" -d "${CONFIG[NEW_DB_NAME]}" \
            --verbose --clean --no-owner --no-privileges \
            --jobs=${CONFIG[PARALLEL_JOBS]} "$backup_dir" &>/dev/null &
        
        local pid=$!
        monitor_restore_progress "${CONFIG[NEW_DB_NAME]}" $pid "Restoring database (parallel)" $source_table_count
        wait $pid
        local restore_result=$?
        
        # Cleanup temp directory
        rm -rf "$temp_dir"
        
    elif [[ "$BACKUP_FILE" == *.sql.gz ]]; then
        # Handle compressed SQL backup
        print_color "$BLUE" "Starting SQL restore from compressed backup..."
        zcat "$BACKUP_FILE" | psql -h "${CONFIG[LOCAL_HOST]}" -p "${CONFIG[LOCAL_PORT]}" -U "${CONFIG[LOCAL_USER]}" -d "${CONFIG[NEW_DB_NAME]}" &>/dev/null &
        local pid=$!
        monitor_restore_progress "${CONFIG[NEW_DB_NAME]}" $pid "Restoring compressed SQL backup" $source_table_count
        wait $pid
        local restore_result=$?
        
    else
        # Handle regular SQL backup
        print_color "$BLUE" "Starting SQL restore from backup file..."
        psql -h "${CONFIG[LOCAL_HOST]}" -p "${CONFIG[LOCAL_PORT]}" -U "${CONFIG[LOCAL_USER]}" -d "${CONFIG[NEW_DB_NAME]}" < "$BACKUP_FILE" &>/dev/null &
        local pid=$!
        monitor_restore_progress "${CONFIG[NEW_DB_NAME]}" $pid "Restoring SQL backup" $source_table_count
        wait $pid
        local restore_result=$?
    fi
    
    if [[ $? -eq 0 ]]; then
        print_color "$GREEN" "${CHECK} Restore completed successfully!"
        log "Database restored: ${CONFIG[NEW_DB_NAME]}"
        return 0
    else
        print_color "$RED" "${CROSS} Restore failed!"
        return 1
    fi
}

# Verify restoration
verify_restoration() {
    print_color "$BLUE" "${GEAR} Verifying restoration..."
    
    export PGPASSWORD="${CONFIG[LOCAL_PASSWORD]}"
    
    local table_count=$(get_table_count "${CONFIG[LOCAL_HOST]}" "${CONFIG[LOCAL_PORT]}" "${CONFIG[LOCAL_USER]}" "${CONFIG[LOCAL_PASSWORD]}" "${CONFIG[NEW_DB_NAME]}")
    local db_size=$(get_db_size "${CONFIG[LOCAL_HOST]}" "${CONFIG[LOCAL_PORT]}" "${CONFIG[LOCAL_USER]}" "${CONFIG[LOCAL_PASSWORD]}" "${CONFIG[NEW_DB_NAME]}")
    
    print_color "$GREEN" "${CHECK} Verification complete!"
    print_color "$CYAN" "   Database: ${CONFIG[NEW_DB_NAME]}"
    print_color "$CYAN" "   Tables: $table_count"
    print_color "$CYAN" "   Size: $db_size"
    
    log "Verification: ${CONFIG[NEW_DB_NAME]} - Tables: $table_count, Size: $db_size"
}

# =============================================================================
# MENU SYSTEM
# =============================================================================

show_menu() {
    clear
    print_header "PostgreSQL Advanced Backup & Restore Tool v2.0"
    
    print_color "$YELLOW" "${DATABASE} Current Configuration:"
    echo
    printf "  %-20s: %s\n" "Remote Database" "${CONFIG[REMOTE_HOST]}:${CONFIG[REMOTE_PORT]}/${CONFIG[REMOTE_DB]}"
    printf "  %-20s: %s\n" "Local Database" "${CONFIG[LOCAL_HOST]}:${CONFIG[LOCAL_PORT]}/${CONFIG[NEW_DB_NAME]}"
    printf "  %-20s: %s\n" "Backup Directory" "${CONFIG[BACKUP_DIR]}"
    printf "  %-20s: %s\n" "Compression" "${CONFIG[COMPRESSION]}"
    echo
    
    print_color "$CYAN" "${GEAR} Available Operations:"
    echo
    print_color "$WHITE" "  1) ${GREEN}Full Backup & Restore${WHITE}     - Complete backup and restore process"
    print_color "$WHITE" "  2) ${BLUE}Backup Only${WHITE}              - Create backup from remote database"
    print_color "$WHITE" "  3) ${MAGENTA}Restore Only${WHITE}             - Restore from existing backup file"
    print_color "$WHITE" "  4) ${YELLOW}Test Connections${WHITE}         - Test remote and local database connections"
    print_color "$WHITE" "  5) ${CYAN}Configuration${WHITE}            - Modify configuration settings"
    print_color "$WHITE" "  6) ${WHITE}View Logs${WHITE}                - Display recent operation logs"
    print_color "$WHITE" "  7) ${WHITE}List Backups${WHITE}             - Show available backup files"
    print_color "$WHITE" "  8) ${RED}Exit${WHITE}                     - Exit the application"
    echo
}

# List available backups
list_backups() {
    print_header "AVAILABLE BACKUPS"
    
    if [[ ! -d "${CONFIG[BACKUP_DIR]}" ]]; then
        print_color "$YELLOW" "No backup directory found."
        return
    fi
    
    local backups=($(find "${CONFIG[BACKUP_DIR]}" -name "*.sql" -o -name "*.sql.gz" -o -name "*.tar.gz" | sort -r))
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        print_color "$YELLOW" "No backup files found in ${CONFIG[BACKUP_DIR]}"
        return
    fi
    
    print_color "$CYAN" "Found ${#backups[@]} backup file(s):"
    echo
    
    for i in "${!backups[@]}"; do
        local backup="${backups[$i]}"
        local filename=$(basename "$backup")
        local size=$(du -h "$backup" | cut -f1)
        local date=$(date -r "$backup" "+%Y-%m-%d %H:%M:%S")
        
        printf "  %2d) %-40s %8s  %s\n" $((i+1)) "$filename" "$size" "$date"
    done
    echo
}

# View recent logs
view_logs() {
    print_header "RECENT OPERATION LOGS"
    
    if [[ ! -d "$LOG_DIR" ]]; then
        print_color "$YELLOW" "No log directory found."
        return
    fi
    
    local latest_log=$(find "$LOG_DIR" -name "*.log" | sort -r | head -1)
    
    if [[ -z "$latest_log" ]]; then
        print_color "$YELLOW" "No log files found."
        return
    fi
    
    print_color "$CYAN" "Latest log file: $(basename "$latest_log")"
    echo
    print_color "$WHITE" "$(tail -20 "$latest_log")"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Initialize
    load_config
    log "Script started"
    
    # Check dependencies
    for cmd in psql pg_dump; do
        if ! command -v "$cmd" &> /dev/null; then
            print_color "$RED" "${CROSS} Required command '$cmd' not found. Please install PostgreSQL client tools."
            exit 1
        fi
    done
    
    # Interactive mode
    if [[ $# -eq 0 ]]; then
        while true; do
            show_menu
            read -p "Select an option (1-8): " choice
            echo
            
            case $choice in
                1)
                    print_header "FULL BACKUP & RESTORE PROCESS"
                    
                    # Test connections first
                    if ! test_connection "${CONFIG[REMOTE_HOST]}" "${CONFIG[REMOTE_PORT]}" "${CONFIG[REMOTE_USER]}" "${CONFIG[REMOTE_PASSWORD]}" "${CONFIG[REMOTE_DB]}" "Remote"; then
                        read -p "Continue anyway? (y/N): " -n 1 -r
                        echo
                        [[ ! $REPLY =~ ^[Yy]$ ]] && continue
                    fi
                    
                    if ! test_connection "${CONFIG[LOCAL_HOST]}" "${CONFIG[LOCAL_PORT]}" "${CONFIG[LOCAL_USER]}" "${CONFIG[LOCAL_PASSWORD]}" "postgres" "Local"; then
                        read -p "Continue anyway? (y/N): " -n 1 -r
                        echo
                        [[ ! $REPLY =~ ^[Yy]$ ]] && continue
                    fi
                    
                    # Perform backup and restore
                    create_backup && restore_backup && verify_restoration
                    
                    # Cleanup option
                    echo
                    read -p "Delete backup file? (y/N): " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        rm -f "$BACKUP_FILE"
                        print_color "$GREEN" "${CHECK} Backup file deleted"
                    else
                        print_color "$BLUE" "Backup file kept: $BACKUP_FILE"
                    fi
                    ;;
                    
                2)
                    print_header "BACKUP ONLY"
                    test_connection "${CONFIG[REMOTE_HOST]}" "${CONFIG[REMOTE_PORT]}" "${CONFIG[REMOTE_USER]}" "${CONFIG[REMOTE_PASSWORD]}" "${CONFIG[REMOTE_DB]}" "Remote" || {
                        read -p "Continue anyway? (y/N): " -n 1 -r
                        echo
                        [[ ! $REPLY =~ ^[Yy]$ ]] && continue
                    }
                    create_backup
                    ;;
                    
                3)
                    print_header "RESTORE ONLY"
                    list_backups
                    read -p "Enter backup file path (or number from list): " input
                    
                    if [[ "$input" =~ ^[0-9]+$ ]]; then
                        local backups=($(find "${CONFIG[BACKUP_DIR]}" -name "*.sql" -o -name "*.sql.gz" -o -name "*.tar.gz" | sort -r))
                        if [[ $input -le ${#backups[@]} && $input -gt 0 ]]; then
                            BACKUP_FILE="${backups[$((input-1))]}"
                        else
                            print_color "$RED" "Invalid selection"
                            continue
                        fi
                    else
                        BACKUP_FILE="$input"
                    fi
                    
                    if [[ ! -f "$BACKUP_FILE" ]]; then
                        print_color "$RED" "${CROSS} Backup file not found: $BACKUP_FILE"
                        continue
                    fi
                    
                    restore_backup && verify_restoration
                    ;;
                    
                4)
                    print_header "CONNECTION TESTS"
                    test_connection "${CONFIG[REMOTE_HOST]}" "${CONFIG[REMOTE_PORT]}" "${CONFIG[REMOTE_USER]}" "${CONFIG[REMOTE_PASSWORD]}" "${CONFIG[REMOTE_DB]}" "Remote"
                    test_connection "${CONFIG[LOCAL_HOST]}" "${CONFIG[LOCAL_PORT]}" "${CONFIG[LOCAL_USER]}" "${CONFIG[LOCAL_PASSWORD]}" "postgres" "Local"
                    ;;
                    
                5)
                    configure_interactive
                    ;;
                    
                6)
                    view_logs
                    ;;
                    
                7)
                    list_backups
                    ;;
                    
                8)
                    print_color "$GREEN" "Thank you for using PostgreSQL Backup & Restore Tool!"
                    log "Script ended normally"
                    exit 0
                    ;;
                    
                *)
                    print_color "$RED" "Invalid option. Please select 1-8."
                    ;;
            esac
            
            echo
            read -p "Press Enter to continue..." -r
        done
    else
        # Command-line mode (for backward compatibility)
        print_header "COMMAND-LINE MODE"
        test_connection "${CONFIG[REMOTE_HOST]}" "${CONFIG[REMOTE_PORT]}" "${CONFIG[REMOTE_USER]}" "${CONFIG[REMOTE_PASSWORD]}" "${CONFIG[REMOTE_DB]}" "Remote"
        test_connection "${CONFIG[LOCAL_HOST]}" "${CONFIG[LOCAL_PORT]}" "${CONFIG[LOCAL_USER]}" "${CONFIG[LOCAL_PASSWORD]}" "postgres" "Local"
        create_backup && restore_backup && verify_restoration
    fi
}

# Script entry point
# Fix for BASH_SOURCE[0] unbound variable when script is piped via curl
if [[ -n "${BASH_SOURCE:-}" && "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
elif [[ -z "${BASH_SOURCE:-}" ]]; then
    # When script is piped, just run main
    main "$@"
fi
