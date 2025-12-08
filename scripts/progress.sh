#!/usr/bin/env bash
# Progress bar utility functions

spinner_help() {
    cat << 'EOF'
NAME
    show_spinner - Display an animated spinner attached to a process

SYNOPSIS
    show_spinner -i|--pid PID [-p|--prepend TEXT] [-a|--append TEXT] [-h|--help]

DESCRIPTION
    Displays an animated spinner that runs while the specified process is active.
    The spinner automatically stops and clears the line when the process terminates.

    This is useful for providing visual feedback during long-running background
    operations without blocking the terminal.

OPTIONS
    -i, --pid PID
        Process ID to monitor. The spinner will animate while this process
        is running. This option is required.

    -p, --prepend TEXT
        Text to display before the spinner animation. Can be used for labels
        like "Processing:" or "Loading:".

    -a, --append TEXT
        Text to display after the spinner animation.

    -h, --help
        Display this help message and exit.

EXAMPLES
    Basic usage with background process:
        sleep 10 & show_spinner -i $!

    With custom text:
        long_command & show_spinner -i $! -p "Working: "

    Multiple spinners for different processes:
        task1 & pid1=$!
        task2 & pid2=$!
        show_spinner -i $pid1 -p "Task 1: " &
        show_spinner -i $pid2 -p "Task 2: "
EOF
}

show_spinner() {
    local pid=""
    local prepend=""
    local append=""
    local spin_array=('|' '/' '-' '\')
    local speed="0.25"

    # Parse options using getopt
    TEMP=$(getopt -o 'i:p:a:h' --long 'pid:,prepend:,append:,help' -n 'show_spinner' -- "$@")
    if [[ $? -ne 0 ]]; then
        echo "Use -h or --help for usage" >&2
        return 1
    fi

    eval set -- "$TEMP"

    while true; do
        case "$1" in
            -i|--pid)
                pid="$2"
                shift 2
                ;;
            -p|--prepend)
                prepend="$2"
                shift 2
                ;;
            -a|--append)
                append="$2"
                shift 2
                ;;
            -h|--help)
                spinner_help
                return 0
                ;;
            --)
                shift
                break
                ;;
            *)
                echo "Usage: show_spinner -i|--pid PID [-p|--prepend PREPEND] [-a|--append APPEND] [-h|--help]" >&2
                echo "Example: sleep 8 & show_spinner -i \$!" >&2
                return 1
                ;;
        esac
    done

    if [[ -z "$pid" ]]; then
        echo "Error: PID is required. Use -i or --pid." >&2
        return 1
    fi

    # Validate PID is a number
    if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
        echo "Error: PID must be a valid process ID number." >&2
        return 1
    fi

    # Animate while process is running
    while kill -0 "$pid" 2>/dev/null; do
        for frame in "${spin_array[@]}"; do
            printf "\r\033[K%s%s%s" "$prepend" "$frame" "$append" >&2
            sleep "$speed"
        done
    done
    # Clear the line after process finishes
    printf "\r%*s\r" "$(tput cols)" "" >&2
}

# Display help for show_progress
progress_help() {
    cat << 'EOF'
NAME
    show_progress - Display an animated progress bar

SYNOPSIS
    show_progress -c|--current CURRENT -t|--total TOTAL
                  [-m|--message MESSAGE] [-w|--width WIDTH] [-h|--help]

DESCRIPTION
    Displays a progress bar showing completion percentage and current/total counts.
    The progress bar fills from left to right as the current value approaches the total.

    This is useful for providing visual feedback during operations with known completion
    metrics like file transfers, processing batches, or any incremental task.

OPTIONS
    -c, --current CURRENT
        Current progress value. Must be a positive integer. This option is required.

    -t, --total TOTAL
        Total expected value for completion. Must be a positive integer. This option is required.

    -m, --message MESSAGE
        Optional text to display before the progress bar.

    -w, --width WIDTH
        Width of the progress bar in characters. Default is 20. Must be a positive integer.

    -h, --help
        Display this help message and exit.

EXAMPLES
    Basic progress bar:
        local max=100
        for i in {1..max}; do
            show_progress -c $i -t max
            sleep 0.1
        done

    In a download script:
        total_size=$(stat -f%z "$file")
        while download_progress; do
            current_size=$(get_downloaded_size)
            show_progress -c $current_size -t $total_size -m "Downloading $file:"
        done

DISPLAY FORMAT
    [MESSAGE] [=====>     ] PERCENT% (CURRENT/TOTAL)
EOF
}

show_progress() {
    local current=""
    local total=""
    local message=""
    local bar_width=20

    # Parse options using getopt
    TEMP=$(getopt -o 'c:t:m:w:h' --long 'current:,total:,message:,width:,help' -n 'show_progress' -- "$@")
    if [[ $? -ne 0 ]]; then
        echo "Use -h or --help for usage" >&2
        return 1
    fi

    eval set -- "$TEMP"

    while true; do
        case "$1" in
            -c|--current)
                current="$2"
                shift 2
                ;;
            -t|--total)
                total="$2"
                shift 2
                ;;
            -m|--message)
                message="$2"
                shift 2
                ;;
            -w|--width)
                bar_width="$2"
                shift 2
                ;;
            -h|--help)
                progress_help
                return 0
                ;;
            --)
                shift
                break
                ;;
            *)
                echo "Use -h or --help for usage" >&2
                return 1
                ;;
        esac
    done

    # Validate required parameters
    if [[ -z "$current" || -z "$total" ]]; then
        echo "Error: current and total are required. Use -c and -t options." >&2
        return 1
    fi

    # Validate current and total are numbers
    if ! [[ "$current" =~ ^[0-9]+$ ]] || ! [[ "$total" =~ ^[0-9]+$ ]]; then
        echo "Error: current and total must be positive integers." >&2
        return 1
    fi

    # Validate bar_width is a number
    if ! [[ "$bar_width" =~ ^[0-9]+$ ]] || (( bar_width < 1 )); then
        echo "Error: width must be a positive integer." >&2
        return 1
    fi

    # Prevent division by zero
    if (( total == 0 )); then
        echo "Error: total cannot be zero." >&2
        return 1
    fi

    if [[ -t 1 ]]; then
        local progress=$(( current * 100 / total ))
        local filled=$(( progress * bar_width / 100 ))
        local empty=$(( bar_width - filled ))

        local bar=""
        if (( filled > 0 )); then
            bar=$(printf '%*s' "$((filled-1))" | tr ' ' '=')
            bar="${bar}>"
        fi

        local spaces=""
        if (( empty > 0 )); then
            spaces=$(printf '%*s' "$empty" | tr ' ' ' ')
        fi

        if [[ -n "$message" ]]; then
            printf "\r\033[K%s [%s%s] %3d%% (%d/%d)" "$message" "$bar" "$spaces" "$progress" "$current" "$total" >&2
        else
            printf "\r\033[K[%s%s] %3d%% (%d/%d)" "$bar" "$spaces" "$progress" "$current" "$total" >&2
        fi
    fi
}

clear_progress() {
    if [[ -t 1 ]]; then
        printf "\r\033[K" >&2
    fi
}
