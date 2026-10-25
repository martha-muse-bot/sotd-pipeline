#!/bin/bash

# SOTD Pipeline WebUI Server Manager
# Manages both frontend (Vite) and backend (FastAPI) servers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_PORT=3000
BACKEND_PORT=8000
PUBLIC_PORT=3200
FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$FRONTEND_DIR/api"
PID_DIR="$FRONTEND_DIR/.pids"

# Create PID directory if it doesn't exist
mkdir -p "$PID_DIR"

# PID files
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
PUBLIC_PID_FILE="$PID_DIR/public.pid"

# Log files
FRONTEND_LOG_FILE="$PID_DIR/frontend.log"
BACKEND_LOG_FILE="$PID_DIR/backend.log"
PUBLIC_LOG_FILE="$PID_DIR/public.log"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%H:%M:%S')] $message${NC}"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    lsof -ti:$port >/dev/null 2>&1
}

# Function to check if a process is running
check_process() {
    local pid_file=$1
    local name=$2
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            # Process is dead, clean up PID file
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Function to kill external processes using a port
kill_external_process() {
    local port=$1
    local process_name=$2
    
    if check_port $port; then
        local pids=$(lsof -ti:$port 2>/dev/null)
        if [[ -n "$pids" ]]; then
            print_status $YELLOW "Killing external process(es) using port $port (PID(s): $pids)..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
            sleep 1
            print_status $GREEN "External process(es) killed"
        fi
    fi
}

# Function to start frontend server
start_frontend() {
    local force=${1:-false}

    if check_process "$FRONTEND_PID_FILE" "frontend"; then
        if [[ "$force" == "true" ]]; then
            stop_server "$FRONTEND_PID_FILE" "frontend" $FRONTEND_PORT
        else
            print_status $YELLOW "Frontend server is already running (PID: $(cat $FRONTEND_PID_FILE))"
            return 0
        fi
    fi
    
    if check_port $FRONTEND_PORT; then
        if [[ "$force" == "true" ]]; then
            kill_external_process $FRONTEND_PORT "frontend"
        else
            print_status $RED "Port $FRONTEND_PORT is already in use by another process"
            print_status $YELLOW "Use --force flag to kill external processes and start anyway"
            return 1
        fi
    fi
    
    print_status $BLUE "Starting frontend server (Vite) on port $FRONTEND_PORT..."
    
    cd "$FRONTEND_DIR"
    ./node_modules/.bin/vite --port $FRONTEND_PORT --host 127.0.0.1 > "$FRONTEND_LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"
    
    # Wait a moment for server to start
    sleep 2
    
    if check_process "$FRONTEND_PID_FILE" "frontend"; then
        print_status $GREEN "Frontend server started successfully (PID: $pid)"
        print_status $BLUE "Frontend URL: http://localhost:$FRONTEND_PORT"
        return 0
    else
        print_status $RED "Failed to start frontend server"
        return 1
    fi
}

# Function to start the public site server (built bundle + /api proxy)
start_public() {
    local force=${1:-false}

    if check_process "$PUBLIC_PID_FILE" "public"; then
        if [[ "$force" == "true" ]]; then
            stop_server "$PUBLIC_PID_FILE" "public" $PUBLIC_PORT
        else
            print_status $YELLOW "Public site server is already running (PID: $(cat $PUBLIC_PID_FILE))"
            return 0
        fi
    fi

    if check_port $PUBLIC_PORT; then
        if [[ "$force" == "true" ]]; then
            kill_external_process $PUBLIC_PORT "public"
        else
            print_status $RED "Port $PUBLIC_PORT is already in use by another process"
            print_status $YELLOW "Use --force flag to kill external processes and start anyway"
            return 1
        fi
    fi

    # The server serves the built bundle; build it if missing.
    if [[ ! -f "$FRONTEND_DIR/dist-public/index.html" ]]; then
        print_status $BLUE "dist-public/ missing - building public bundle..."
        cd "$FRONTEND_DIR"
        npm run build:public > "$PUBLIC_LOG_FILE" 2>&1
    fi

    print_status $BLUE "Starting public site server on port $PUBLIC_PORT..."

    cd "$FRONTEND_DIR"
    node scripts/serve-public.mjs > "$PUBLIC_LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PUBLIC_PID_FILE"

    # Wait a moment for server to start
    sleep 1

    if check_process "$PUBLIC_PID_FILE" "public"; then
        print_status $GREEN "Public site server started successfully (PID: $pid)"
        print_status $BLUE "Public URL: http://localhost:$PUBLIC_PORT"
        return 0
    else
        print_status $RED "Failed to start public site server (see $PUBLIC_LOG_FILE)"
        return 1
    fi
}

# Function to start backend server
start_backend() {
    local force=${1:-false}

    if check_process "$BACKEND_PID_FILE" "backend"; then
        if [[ "$force" == "true" ]]; then
            stop_server "$BACKEND_PID_FILE" "backend" $BACKEND_PORT
        else
            print_status $YELLOW "Backend server is already running (PID: $(cat $BACKEND_PID_FILE))"
            return 0
        fi
    fi
    
    if check_port $BACKEND_PORT; then
        if [[ "$force" == "true" ]]; then
            kill_external_process $BACKEND_PORT "backend"
        else
            print_status $RED "Port $BACKEND_PORT is already in use by another process"
            print_status $YELLOW "Use --force flag to kill external processes and start anyway"
            return 1
        fi
    fi
    
    print_status $BLUE "Starting backend server (FastAPI) on port $BACKEND_PORT..."
    
    # Run from webui directory with proper PYTHONPATH
    cd "$FRONTEND_DIR"
    # Set test environment for CORS to allow all origins during testing
    # Set debug environment for enhanced logging
    # Activate virtual environment and run backend server
    source ../.venv/bin/activate && ENVIRONMENT=test DEBUG=true PYTHONPATH=. python -m uvicorn api.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload --log-level debug > "$BACKEND_LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$BACKEND_PID_FILE"
    
    # Wait a moment for server to start
    sleep 3
    
    if check_process "$BACKEND_PID_FILE" "backend"; then
        print_status $GREEN "Backend server started successfully (PID: $pid)"
        print_status $BLUE "Backend URL: http://localhost:$BACKEND_PORT"
        return 0
    else
        print_status $RED "Failed to start backend server"
        return 1
    fi
}

# Function to stop a server
stop_server() {
    local pid_file=$1
    local name=$2
    local port=$3
    
    if check_process "$pid_file" "$name"; then
        local pid=$(cat "$pid_file")
        print_status $BLUE "Stopping $name server (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        
        # Wait for process to stop
        local count=0
        while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
            sleep 0.5
            count=$((count + 1))
        done
        
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            print_status $YELLOW "Force killing $name server..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        rm -f "$pid_file"
        print_status $GREEN "$name server stopped"
    else
        print_status $YELLOW "$name server is not running (no PID file)"
    fi

    # Always free the port: covers lost PID files, orphaned children (e.g. uvicorn
    # --reload), and servers started outside this script (npm run serve:public).
    if [[ -n "$port" ]] && check_port "$port"; then
        kill_external_process "$port" "$name"
    fi
}

# Function to check server status
check_status() {
    print_status $BLUE "=== WebUI Server Status ==="
    
    # Check frontend
    if check_process "$FRONTEND_PID_FILE" "frontend"; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        print_status $GREEN "Frontend (Vite): RUNNING (PID: $pid, Port: $FRONTEND_PORT)"
    else
        print_status $RED "Frontend (Vite): STOPPED"
    fi
    
    # Check backend
    if check_process "$BACKEND_PID_FILE" "backend"; then
        local pid=$(cat "$BACKEND_PID_FILE")
        print_status $GREEN "Backend (FastAPI): RUNNING (PID: $pid, Port: $BACKEND_PORT)"
    else
        print_status $RED "Backend (FastAPI): STOPPED"
    fi

    # Check public site
    if check_process "$PUBLIC_PID_FILE" "public"; then
        local pid=$(cat "$PUBLIC_PID_FILE")
        print_status $GREEN "Public site: RUNNING (PID: $pid, Port: $PUBLIC_PORT)"
    else
        print_status $RED "Public site: STOPPED"
    fi
    
    # Check ports
    if check_port $FRONTEND_PORT; then
        print_status $GREEN "Port $FRONTEND_PORT: IN USE"
    else
        print_status $RED "Port $FRONTEND_PORT: AVAILABLE"
    fi
    
    if check_port $BACKEND_PORT; then
        print_status $GREEN "Port $BACKEND_PORT: IN USE"
    else
        print_status $RED "Port $BACKEND_PORT: AVAILABLE"
    fi

    if check_port $PUBLIC_PORT; then
        print_status $GREEN "Port $PUBLIC_PORT: IN USE"
    else
        print_status $RED "Port $PUBLIC_PORT: AVAILABLE"
    fi
}

# Function to show logs
show_logs() {
    local server=$1
    
    case $server in
        frontend)
            if [[ -f "$FRONTEND_LOG_FILE" ]]; then
                print_status $BLUE "=== Frontend Server Logs ==="
                tail -f "$FRONTEND_LOG_FILE"
            else
                print_status $RED "No frontend log file found"
            fi
            ;;
        backend)
            if [[ -f "$BACKEND_LOG_FILE" ]]; then
                print_status $BLUE "=== Backend Server Logs ==="
                tail -f "$BACKEND_LOG_FILE"
            else
                print_status $RED "No backend log file found"
            fi
            ;;
        public)
            if [[ -f "$PUBLIC_LOG_FILE" ]]; then
                print_status $BLUE "=== Public Site Logs ==="
                tail -f "$PUBLIC_LOG_FILE"
            else
                print_status $RED "No public log file found"
            fi
            ;;
        api-debug)
            local api_debug_log="$FRONTEND_DIR/logs/api_debug.log"
            if [[ -f "$api_debug_log" ]]; then
                print_status $BLUE "=== API Debug Logs ==="
                tail -f "$api_debug_log"
            else
                print_status $RED "No API debug log file found at $api_debug_log"
            fi
            ;;
        api-errors)
            local api_errors_log="$FRONTEND_DIR/logs/api_errors.log"
            if [[ -f "$api_errors_log" ]]; then
                print_status $BLUE "=== API Error Logs ==="
                tail -f "$api_errors_log"
            else
                print_status $RED "No API error log file found at $api_errors_log"
            fi
            ;;
        *)
            print_status $RED "Usage: $0 logs [frontend|backend|api-debug|api-errors]"
            exit 1
            ;;
    esac
}

# Function to show help
show_help() {
    echo "SOTD Pipeline WebUI Server Manager"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start       Start frontend, backend, and public site servers"
    echo "  stop        Stop all servers"
    echo "  restart     Restart both servers"
    echo "  status      Show status of both servers"
    echo "  logs [server] Show logs for specified server (frontend|backend|public|api-debug|api-errors)"
    echo "  clean       Clean up PID files and logs"
    echo "  help        Show this help message"
    echo ""
    echo "Options:"
    echo "  --force     Kill external processes using required ports before starting"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start all servers"
    echo "  $0 start --force  # Start servers, killing external processes if needed"
    echo "  $0 stop           # Stop all servers"
    echo "  $0 status         # Check server status"
    echo "  $0 logs frontend  # Show frontend logs"
    echo "  $0 logs backend   # Show backend logs"
    echo "  $0 logs api-debug # Show API debug logs"
    echo "  $0 logs api-errors # Show API error logs"
    echo ""
    echo "Server URLs:"
    echo "  Frontend (admin dev): http://localhost:$FRONTEND_PORT"
    echo "  Public site:          http://localhost:$PUBLIC_PORT"
    echo "  Backend:              http://localhost:$BACKEND_PORT"
}

# Function to clean up
cleanup() {
    print_status $BLUE "Cleaning up PID files and logs..."
    rm -f "$FRONTEND_PID_FILE" "$BACKEND_PID_FILE" "$PUBLIC_PID_FILE"
    rm -f "$FRONTEND_LOG_FILE" "$BACKEND_LOG_FILE" "$PUBLIC_LOG_FILE"
    print_status $GREEN "Cleanup complete"
}

# Parse command line arguments
COMMAND="${1:-help}"
FORCE=false

# Accept --force anywhere in the args (restart --force / --force restart)
for arg in "$@"; do
    if [[ "$arg" == "--force" ]]; then
        FORCE=true
    fi
done
# If first arg is --force, treat the next token as the command
if [[ "$COMMAND" == "--force" ]]; then
    COMMAND="${2:-help}"
fi

# Main script logic
case "$COMMAND" in
    start)
        print_status $BLUE "Starting SOTD Pipeline WebUI servers..."
        if [[ "$FORCE" == "true" ]]; then
            print_status $YELLOW "Force mode enabled - will kill external processes if needed"
        fi
        start_frontend "$FORCE"
        start_backend "$FORCE"
        start_public "$FORCE"
        print_status $GREEN "All servers started!"
        print_status $BLUE "Frontend (admin dev): http://localhost:$FRONTEND_PORT"
        print_status $BLUE "Public site:          http://localhost:$PUBLIC_PORT"
        print_status $BLUE "Backend:              http://localhost:$BACKEND_PORT"
        ;;
    stop)
        print_status $BLUE "Stopping SOTD Pipeline WebUI servers..."
        stop_server "$FRONTEND_PID_FILE" "frontend" $FRONTEND_PORT
        stop_server "$BACKEND_PID_FILE" "backend" $BACKEND_PORT
        stop_server "$PUBLIC_PID_FILE" "public" $PUBLIC_PORT
        print_status $GREEN "All servers stopped!"
        ;;
    restart)
        print_status $BLUE "Restarting SOTD Pipeline WebUI servers..."
        if [[ "$FORCE" == "true" ]]; then
            print_status $YELLOW "Force mode enabled - will kill external processes if needed"
        fi
        stop_server "$FRONTEND_PID_FILE" "frontend" $FRONTEND_PORT
        stop_server "$BACKEND_PID_FILE" "backend" $BACKEND_PORT
        stop_server "$PUBLIC_PID_FILE" "public" $PUBLIC_PORT
        sleep 2
        start_frontend "$FORCE"
        start_backend "$FORCE"
        start_public "$FORCE"
        print_status $GREEN "All servers restarted!"
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs "${2:-}"
        ;;
    clean)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_status $RED "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 