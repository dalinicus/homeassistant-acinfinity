FROM homeassistant/home-assistant:stable

# Install development tools
RUN apk add --no-cache \
    git \
    bash \
    curl \
    vim \
    nano \
    build-base \
    linux-headers

# Create config directory structure
RUN mkdir -p /config/custom_components /config/.storage

# Set working directory
WORKDIR /workspaces/homeassistant-acinfinity

# Expose Home Assistant port
EXPOSE 8123
