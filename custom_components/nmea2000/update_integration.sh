#!/bin/bash

# ==== CONFIGURATION ====
GITHUB_USER="tomer-w"
GITHUB_REPO="ha-nmea2000"
TARGET_SUBFOLDER="custom_components/nmea2000"
DEST_FOLDER="/config/custom_components/nmea2000"
# ========================
# Usage:
# Run the script without arguments to update the integration.
# Use the --restart flag to restart Home Assistant after updating.
# Example: bash update_integration.sh --restart

RESTART_HA=false
if [[ "$1" == "--restart" ]]; then
    RESTART_HA=true
fi

# Fetch latest release tag via GitHub API
LATEST_TAG=$(curl -s "https://api.github.com/repos/$GITHUB_USER/$GITHUB_REPO/releases/latest" | jq -r .tag_name)

if [ "$LATEST_TAG" == "null" ] || [ -z "$LATEST_TAG" ]; then
    echo "⚠️  No releases found. Falling back to main branch."
    ZIP_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO/archive/refs/heads/main.zip"
    TMP_FOLDER="$GITHUB_REPO-main"
else
    echo "⬇️  Found latest release: $LATEST_TAG"
    ZIP_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO/archive/refs/tags/$LATEST_TAG.zip"
    TMP_FOLDER="$GITHUB_REPO-$LATEST_TAG"
fi

# Create temp dir
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR" || exit 1

# Download and extract
echo "📦 Downloading from $ZIP_URL"
wget -q "$ZIP_URL" -O latest.zip || curl -L "$ZIP_URL" -o latest.zip
unzip -q latest.zip

# Copy the integration folder to destination
mkdir -p "$DEST_FOLDER"
cp -r "$TMP_FOLDER/$TARGET_SUBFOLDER/"* "$DEST_FOLDER/"
chmod +x "$DEST_FOLDER/"update_integration.sh
echo "✅ Integration updated at $DEST_FOLDER"

# Cleanup
cd /
rm -rf "$TMP_DIR"

# Restart Home Assistant if requested
if [ "$RESTART_HA" = true ]; then
    echo "🧪 Validating Home Assistant configuration..."
    if ha core check; then
        echo "✅ Configuration is valid."
        echo "🔁 Restarting Home Assistant..."
        ha core restart
        echo "✅ Restart command issued."
    else
        echo "❌ Configuration is invalid. Skipping restart."
        exit 1
    fi
fi