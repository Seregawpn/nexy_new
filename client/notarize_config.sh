#!/bin/bash
# Конфигурация для нотаризации Nexy AI Voice Assistant

# Apple ID для нотаризации
export APPLE_ID="seregawpn@gmail.com"

# App-Specific Password (создайте в appleid.apple.com)
export APP_PASSWORD="qtiv-kabm-idno-qmbl"

# Team ID
export TEAM_ID="5NKLL2CLB9"

# Bundle ID
export BUNDLE_ID="com.sergiyzasorin.nexy.voiceassistant"

echo "🔐 Конфигурация нотаризации:"
echo "   Apple ID: $APPLE_ID"
echo "   Team ID: $TEAM_ID"
echo "   Bundle ID: $BUNDLE_ID"
echo "   App Password: ${APP_PASSWORD:0:4}****"
