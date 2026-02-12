#!/usr/bin/env bash
# WiFi Watchdog — recovers wlan0 on connectivity loss.
# Designed to run as a systemd service on the Pi.
#
# Escalation chain on failure:
#   1 fail:  wpa_cli reassociate (quick reconnect)
#   2 fails: ip link down/up + wpa_cli reconfigure
#   3 fails: full restart of wpa_supplicant + dhcpcd
#
# Also disables WiFi power management on startup to prevent
# the ~30 min idle disconnects from the Pi's wireless chip.

PING_INTERVAL=30
INTERFACE="wlan0"

fail_count=0

get_gateway() {
    ip route | awk '/default/ { print $3; exit }'
}

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') wifi-watchdog: $*"
}

# Disable WiFi power management — this is the #1 cause of idle disconnects
log "Disabling WiFi power management on $INTERFACE"
sudo iw "$INTERFACE" set power_save off 2>/dev/null && \
    log "Power save disabled" || \
    log "Warning: could not disable power save (interface may not be up yet)"

log "Starting WiFi watchdog (interface=$INTERFACE, interval=${PING_INTERVAL}s)"

while true; do
    # Determine ping target (re-check each cycle in case gateway changes)
    PING_TARGET=$(get_gateway)
    if [ -z "$PING_TARGET" ]; then
        PING_TARGET="8.8.8.8"
    fi

    if ping -c 1 -W 5 "$PING_TARGET" > /dev/null 2>&1; then
        if [ "$fail_count" -gt 0 ]; then
            log "Connectivity restored after $fail_count failure(s)"
            # Re-disable power save after any recovery (gets reset on reconnect)
            sudo iw "$INTERFACE" set power_save off 2>/dev/null
        fi
        fail_count=0
    else
        fail_count=$((fail_count + 1))
        log "Ping to $PING_TARGET failed ($fail_count)"

        if [ "$fail_count" -eq 1 ]; then
            # Level 1: Quick reassociate via wpa_cli
            log "Level 1: wpa_cli reassociate"
            wpa_cli -i "$INTERFACE" reassociate 2>/dev/null
            sleep 5

        elif [ "$fail_count" -eq 2 ]; then
            # Level 2: Bounce interface + reconfigure WPA
            log "Level 2: interface bounce + wpa_cli reconfigure"
            sudo ip link set "$INTERFACE" down
            sleep 2
            sudo ip link set "$INTERFACE" up
            sleep 5
            wpa_cli -i "$INTERFACE" reconfigure 2>/dev/null
            sleep 10

        elif [ "$fail_count" -ge 3 ]; then
            # Level 3: Nuclear — restart networking services
            log "Level 3: restarting wpa_supplicant and dhcpcd"
            sudo systemctl restart wpa_supplicant 2>/dev/null
            sleep 5
            sudo systemctl restart dhcpcd 2>/dev/null
            sleep 15

            # Re-disable power save after full restart
            sudo iw "$INTERFACE" set power_save off 2>/dev/null

            fail_count=0
        fi
    fi

    sleep "$PING_INTERVAL"
done
