#!/bin/bash
# Verifica se sistema está pronto para benchmark

echo "=== System Readiness Check ==="

# CPU Temperature (with fallback if sensors not available)
if command -v sensors &> /dev/null; then
    TEMP=$(sensors 2>/dev/null | grep 'Core 0' | awk '{print $3}' | sed 's/[+°C]//g')
    if [ -n "$TEMP" ]; then
        TEMP_INT=${TEMP%.*}
        if [ "$TEMP_INT" -gt 70 ]; then
            echo "❌ CPU Temp: $TEMP°C (> 70°C) - Wait for cooling"
            exit 1
        else
            echo "✅ CPU Temp: $TEMP°C (< 70°C)"
        fi
    else
        echo "⚠️  CPU Temp: sensors found but no Core 0 data - skipping check"
    fi
else
    echo "⚠️  CPU Temp: sensors not installed - skipping check"
fi

# System Load (with fallback if bc not available)
LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | xargs)
if command -v bc &> /dev/null; then
    if (( $(echo "$LOAD > 1.0" | bc -l) )); then
        echo "❌ System Load: $LOAD (> 1.0) - Wait for idle"
        exit 1
    else
        echo "✅ System Load: $LOAD (< 1.0)"
    fi
else
    # Fallback: compare integer part only
    LOAD_INT=${LOAD%.*}
    if [ "$LOAD_INT" -ge 1 ]; then
        echo "❌ System Load: $LOAD (>= 1.0) - Wait for idle"
        exit 1
    else
        echo "✅ System Load: $LOAD (< 1.0)"
    fi
fi

# Memory Available
MEM_AVAIL=$(free -m | awk 'NR==2{printf "%.0f", $7}')
if [ "$MEM_AVAIL" -lt 2048 ]; then
    echo "❌ Memory: ${MEM_AVAIL}MB (< 2GB) - Close applications"
    exit 1
else
    echo "✅ Memory: ${MEM_AVAIL}MB (> 2GB)"
fi

echo ""
echo "✅ System ready for benchmark"
