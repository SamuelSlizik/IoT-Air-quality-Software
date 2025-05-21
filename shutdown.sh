cat > shutdown.sh <<'EOF'
#!/bin/sh
# Calls the host’s real shutdown binary
exec /host-sbin-shutdown now
EOF

chmod +x shutdown.sh
