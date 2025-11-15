#!/usr/bin/env bash
# =============================================================================
# Neo4j Database Restore Script
# =============================================================================
#
# This script restores a Neo4j database from a backup created by backup_neo4j.sh.
# Features:
#   - Interactive backup selection
#   - Pre-restore validation (checksum, integrity)
#   - Automatic current database backup before restore
#   - Post-restore verification (node/relationship counts)
#   - Rollback capability on failure
#
# Usage:
#   bash infrastructure/scripts/restore_neo4j.sh [backup_file.dump.gz]
#
#   # Interactive mode (list available backups)
#   bash infrastructure/scripts/restore_neo4j.sh
#
#   # Direct restore from specific backup
#   bash infrastructure/scripts/restore_neo4j.sh backups/neo4j/neo4j_merl-t-kg_20250115_030000.dump.gz
#
# IMPORTANT:
#   - This will STOP the Neo4j container during restore
#   - Current database will be backed up before restore (safety measure)
#   - Restore can take 30 minutes to 2 hours depending on backup size
#   - Ensure sufficient disk space (2x backup size)
#
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.production"

# Default values
DEFAULT_BACKUP_DIR="${PROJECT_ROOT}/backups/neo4j"
DEFAULT_DATABASE_NAME="merl-t-kg"
CONTAINER_NAME="merl-t-neo4j-production"

# Load environment variables
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    source <(grep -E '^(NEO4J_BACKUP_DIR|NEO4J_DATABASE_NAME)=' "${ENV_FILE}" | sed 's/^/export /')
fi

BACKUP_DIR="${NEO4J_BACKUP_DIR:-$DEFAULT_BACKUP_DIR}"
DATABASE_NAME="${NEO4J_DATABASE_NAME:-$DEFAULT_DATABASE_NAME}"

# Safety backup before restore
SAFETY_BACKUP_DIR="${BACKUP_DIR}/safety_backups"
SAFETY_BACKUP_FILE="${SAFETY_BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).dump.gz"

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "${MAGENTA}============================================================${NC}"
    echo -e "${MAGENTA}  Neo4j Database Restore - $(date)${NC}"
    echo -e "${MAGENTA}============================================================${NC}"
    echo ""
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

print_step() {
    echo -e "${CYAN}➜${NC} $1"
}

check_dependencies() {
    print_info "Checking dependencies..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker not found"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker daemon not running"
        exit 1
    fi

    if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_error "Container '${CONTAINER_NAME}' not found"
        exit 1
    fi

    print_info "Dependencies OK"
}

list_available_backups() {
    print_info "Available backups in ${BACKUP_DIR}:"
    echo ""

    local backups=()
    local index=1

    while IFS= read -r backup_file; do
        backups+=("${backup_file}")

        local filename
        filename=$(basename "${backup_file}")

        local size
        size=$(du -h "${backup_file}" | cut -f1)

        local date_str
        date_str=$(stat -f%Sm -t "%Y-%m-%d %H:%M:%S" "${backup_file}" 2>/dev/null || \
                   stat -c"%y" "${backup_file}" 2>/dev/null | cut -d'.' -f1)

        # Check if metadata exists
        local metadata_file="${backup_file}.metadata.json"
        local node_count="N/A"
        local rel_count="N/A"

        if [[ -f "${metadata_file}" ]]; then
            node_count=$(jq -r '.node_count // "N/A"' "${metadata_file}" 2>/dev/null || echo "N/A")
            rel_count=$(jq -r '.relationship_count // "N/A"' "${metadata_file}" 2>/dev/null || echo "N/A")
        fi

        echo -e "  ${CYAN}[${index}]${NC} ${filename}"
        echo -e "      Date: ${date_str}"
        echo -e "      Size: ${size}"
        echo -e "      Nodes: ${node_count} | Relationships: ${rel_count}"
        echo ""

        ((index++))
    done < <(find "${BACKUP_DIR}" -maxdepth 1 -name "neo4j_*.dump.gz" -type f | sort -r)

    if [[ ${#backups[@]} -eq 0 ]]; then
        print_warn "No backups found in ${BACKUP_DIR}"
        return 1
    fi

    # Store backups array for later use
    echo "${backups[@]}"
}

select_backup_interactive() {
    local available_backups
    available_backups=$(list_available_backups)

    if [[ -z "${available_backups}" ]]; then
        print_error "No backups available"
        exit 1
    fi

    # Convert to array
    local backups_array=($available_backups)

    echo -e "${YELLOW}Select backup to restore:${NC}"
    read -rp "Enter backup number (1-${#backups_array[@]}) or 'q' to quit: " selection

    if [[ "${selection}" == "q" ]]; then
        print_info "Restore cancelled"
        exit 0
    fi

    if ! [[ "${selection}" =~ ^[0-9]+$ ]] || [[ ${selection} -lt 1 ]] || [[ ${selection} -gt ${#backups_array[@]} ]]; then
        print_error "Invalid selection: ${selection}"
        exit 1
    fi

    local selected_index=$((selection - 1))
    echo "${backups_array[$selected_index]}"
}

validate_backup_file() {
    local backup_file=$1

    print_step "Validating backup file..."

    if [[ ! -f "${backup_file}" ]]; then
        print_error "Backup file not found: ${backup_file}"
        return 1
    fi

    # Test gzip integrity
    print_info "Testing archive integrity..."
    if ! gzip -t "${backup_file}" 2>&1; then
        print_error "Backup archive is corrupted"
        return 1
    fi
    print_info "✓ Archive integrity OK"

    # Verify checksum if metadata exists
    local metadata_file="${backup_file}.metadata.json"
    if [[ -f "${metadata_file}" ]]; then
        print_info "Verifying checksum..."

        local expected_checksum
        expected_checksum=$(jq -r '.sha256_checksum' "${metadata_file}")

        local actual_checksum
        actual_checksum=$(sha256sum "${backup_file}" 2>/dev/null | awk '{print $1}' || \
                          shasum -a 256 "${backup_file}" | awk '{print $1}')

        if [[ "${expected_checksum}" == "${actual_checksum}" ]]; then
            print_info "✓ Checksum verified"
        else
            print_error "Checksum mismatch!"
            print_error "  Expected: ${expected_checksum}"
            print_error "  Actual:   ${actual_checksum}"
            return 1
        fi
    else
        print_warn "No metadata file found. Skipping checksum verification."
    fi

    return 0
}

display_backup_info() {
    local backup_file=$1

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Backup Information${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local metadata_file="${backup_file}.metadata.json"

    if [[ -f "${metadata_file}" ]]; then
        echo -e "  File:         $(basename "${backup_file}")"
        echo -e "  Date:         $(jq -r '.backup_date' "${metadata_file}")"
        echo -e "  Database:     $(jq -r '.database_name' "${metadata_file}")"
        echo -e "  Neo4j Ver:    $(jq -r '.neo4j_version' "${metadata_file}")"
        echo -e "  Size:         $(jq -r '.file_size_human' "${metadata_file}")"
        echo -e "  Nodes:        $(jq -r '.node_count' "${metadata_file}")"
        echo -e "  Relationships: $(jq -r '.relationship_count' "${metadata_file}")"
    else
        echo -e "  File:         $(basename "${backup_file}")"
        echo -e "  Size:         $(du -h "${backup_file}" | cut -f1)"
        echo -e "  ${YELLOW}No metadata available${NC}"
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

confirm_restore() {
    echo -e "${YELLOW}⚠️  WARNING: This will REPLACE the current database!${NC}"
    echo -e "${YELLOW}⚠️  The Neo4j container will be stopped during restore.${NC}"
    echo ""
    echo -e "Current database will be backed up to:"
    echo -e "  ${SAFETY_BACKUP_FILE}"
    echo ""
    read -rp "Are you sure you want to proceed? (yes/no): " confirmation

    if [[ "${confirmation}" != "yes" ]]; then
        print_info "Restore cancelled"
        exit 0
    fi
}

create_safety_backup() {
    print_step "Creating safety backup of current database..."

    mkdir -p "${SAFETY_BACKUP_DIR}"

    # Dump current database
    if docker exec "${CONTAINER_NAME}" \
        neo4j-admin database dump \
        --database="${DATABASE_NAME}" \
        --to-path=/backups/safety_backups \
        --overwrite-destination=true \
        "$(basename "${SAFETY_BACKUP_FILE%.gz}")" 2>&1; then

        # Compress
        docker exec "${CONTAINER_NAME}" \
            gzip -9 "/backups/safety_backups/$(basename "${SAFETY_BACKUP_FILE%.gz}")"

        print_info "✓ Safety backup created: ${SAFETY_BACKUP_FILE}"
    else
        print_error "Failed to create safety backup"
        return 1
    fi
}

stop_neo4j() {
    print_step "Stopping Neo4j container..."

    if docker stop "${CONTAINER_NAME}" &> /dev/null; then
        print_info "✓ Neo4j stopped"
    else
        print_error "Failed to stop Neo4j"
        return 1
    fi
}

start_neo4j() {
    print_step "Starting Neo4j container..."

    if docker start "${CONTAINER_NAME}" &> /dev/null; then
        print_info "Neo4j started. Waiting for readiness..."

        # Wait for Neo4j to be ready (max 2 minutes)
        local max_wait=120
        local waited=0

        while [[ ${waited} -lt ${max_wait} ]]; do
            if docker exec "${CONTAINER_NAME}" \
                cypher-shell -u neo4j -p "${NEO4J_AUTH#*/}" \
                "RETURN 1" &> /dev/null; then
                print_info "✓ Neo4j is ready"
                return 0
            fi

            sleep 5
            waited=$((waited + 5))
            echo -n "."
        done

        echo ""
        print_error "Neo4j failed to become ready after ${max_wait} seconds"
        return 1
    else
        print_error "Failed to start Neo4j"
        return 1
    fi
}

perform_restore() {
    local backup_file=$1

    print_step "Restoring database from backup..."

    # Copy backup to container
    local backup_filename
    backup_filename=$(basename "${backup_file}")
    local temp_backup="/tmp/${backup_filename}"

    print_info "Copying backup to container..."
    if ! docker cp "${backup_file}" "${CONTAINER_NAME}:${temp_backup}"; then
        print_error "Failed to copy backup to container"
        return 1
    fi

    # Decompress inside container
    print_info "Decompressing backup..."
    if ! docker exec "${CONTAINER_NAME}" gunzip "${temp_backup}"; then
        print_error "Failed to decompress backup"
        return 1
    fi

    local uncompressed_backup="${temp_backup%.gz}"

    # Load dump
    print_info "Loading database dump (this may take several minutes)..."
    local start_time
    start_time=$(date +%s)

    if docker exec "${CONTAINER_NAME}" \
        neo4j-admin database load \
        --from-path=/tmp \
        --database="${DATABASE_NAME}" \
        --overwrite-destination=true \
        "$(basename "${uncompressed_backup}")" 2>&1; then

        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))

        print_info "✓ Database restored in ${duration} seconds"

        # Cleanup temp files
        docker exec "${CONTAINER_NAME}" rm -f "${uncompressed_backup}"

        return 0
    else
        print_error "Database restore failed"
        return 1
    fi
}

verify_restore() {
    print_step "Verifying restored database..."

    # Get node count
    local node_count
    node_count=$(docker exec "${CONTAINER_NAME}" \
        cypher-shell -u neo4j -p "${NEO4J_AUTH#*/}" \
        "MATCH (n) RETURN count(n) AS count;" 2>/dev/null | tail -2 | head -1 | tr -d '"' || echo "0")

    # Get relationship count
    local rel_count
    rel_count=$(docker exec "${CONTAINER_NAME}" \
        cypher-shell -u neo4j -p "${NEO4J_AUTH#*/}" \
        "MATCH ()-[r]->() RETURN count(r) AS count;" 2>/dev/null | tail -2 | head -1 | tr -d '"' || echo "0")

    print_info "Current database statistics:"
    print_info "  Nodes: ${node_count}"
    print_info "  Relationships: ${rel_count}"

    if [[ ${node_count} -eq 0 ]]; then
        print_warn "Database has 0 nodes. This might indicate a problem."
        return 1
    fi

    print_info "✓ Database verification passed"
    return 0
}

# =============================================================================
# Main execution
# =============================================================================

main() {
    print_header

    check_dependencies

    # Determine backup file to restore
    local backup_file

    if [[ $# -eq 0 ]]; then
        # Interactive mode
        backup_file=$(select_backup_interactive)
    else
        # Direct mode
        backup_file=$1
    fi

    # Validate backup
    if ! validate_backup_file "${backup_file}"; then
        print_error "Backup validation failed"
        exit 1
    fi

    # Display backup info
    display_backup_info "${backup_file}"

    # Confirm restore
    confirm_restore

    # Create safety backup
    if ! create_safety_backup; then
        print_error "Failed to create safety backup. Aborting restore."
        exit 1
    fi

    # Stop Neo4j
    if ! stop_neo4j; then
        print_error "Failed to stop Neo4j. Aborting restore."
        exit 1
    fi

    # Perform restore
    if perform_restore "${backup_file}"; then
        # Start Neo4j
        if start_neo4j && verify_restore; then
            echo ""
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}  ✓ Restore completed successfully!${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo ""
            print_info "Database: ${DATABASE_NAME}"
            print_info "Restored from: $(basename "${backup_file}")"
            print_info "Safety backup: ${SAFETY_BACKUP_FILE}"
            echo ""
            exit 0
        else
            print_error "Post-restore verification failed"

            # Attempt rollback
            print_warn "Attempting rollback from safety backup..."
            if perform_restore "${SAFETY_BACKUP_FILE}" && start_neo4j; then
                print_warn "Rollback completed. Database restored to pre-restore state."
            else
                print_error "Rollback failed! Database may be in inconsistent state."
                print_error "Manual intervention required."
            fi

            exit 1
        fi
    else
        print_error "Restore failed"

        # Attempt rollback
        print_warn "Attempting rollback from safety backup..."
        if perform_restore "${SAFETY_BACKUP_FILE}" && start_neo4j; then
            print_warn "Rollback completed. Database restored to pre-restore state."
        else
            print_error "Rollback failed! Database may be in inconsistent state."
        fi

        exit 1
    fi
}

# Run main
main "$@"
