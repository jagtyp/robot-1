#!/usr/bin/env bash
# WiFi Watchdog — restarts wlan0 on connectivity loss.
# Designed to run as a systemd service on the Pi.

PING_TARGET=""  # Will be set to default gateway, or fallback to 8.8.8.8
PING_INTERVAL=30
MAX_FAILURES=3
INTERFACE="wlan0"

fail_count=0

get_gateway() {
    ip route | awk '/default/ { print $3; exit }'
}

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') wifi-watchdog: $*"
}

log "Starting WiFi watchdog (interface=$INTERFACE, interval=${PING_INTERVAL}s, max_failures=$MAX_FAILURES)"

while true; do
    # Determine ping target (re-check each cycle in case gateway changes)
    PING_TARGET=$(get_gateway)
    if [ -z "$PING_TARGET" ]; then
        PING_TARGET="8.8.8.8"
    fi

    if ping -c 1 -W 5 "$PING_TARGET" > /dev/null 2>&1; then
        if [ "$fail_count" -gt 0 ]; then
            log "Connectivity restored (was at $fail_count failures)"
        fi
        fail_count=0
    else
        fail_count=$((fail_count + 1))
        log "Ping to $PING_TARGET failed ($fail_count/$MAX_FAILURES)"

        if [ "$fail_count" -ge "$MAX_FAILURES" ]; then
            log "Max failures reached — restarting $INTERFACE"
            sudo ip link set "$INTERFACE" down
            sleep 2
            sudo ip link set "$INTERFACE" up
            sleep 10

            # Check if that fixed it
            if ping -c 1 -W 5 "$PING_TARGET" > /dev/null 2>&1; then
                log "Interface restart fixed connectivity"
                fail_count=0
            else
                log "Interface restart did not help — restarting dhcpcd"
                sudo systemctl restart dhcpcd 2>/dev/null || \
                    sudo systemctl restart wpa_supplicant 2>/dev/null
                sleep 10
            fi

            fail_count=0
        fi
    fi

    sleep "$PING_INTERVAL"
done
