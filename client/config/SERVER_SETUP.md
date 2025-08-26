# External Server Setup Guide

## Overview
This guide explains how to configure the AI Voice Assistant to work with an external server.

## Configuration Steps

### 1. Update Server IP
Edit `app_config.yaml` and replace `YOUR_EXTERNAL_SERVER_IP` with your actual server IP address:

```yaml
grpc:
  server_host: "YOUR_ACTUAL_SERVER_IP"  # Replace with real IP
  server_port: 50051
  timeout: 30
  retry_attempts: 3
  retry_delay: 1
```

### 2. Network Requirements
- Server must be accessible from the internet
- Port 50051 must be open for gRPC connections
- Firewall must allow incoming connections on port 50051

### 3. SSL/TLS Configuration (Recommended)
For production use, configure SSL/TLS:
- Generate SSL certificates
- Update gRPC server to use SSL
- Update client configuration for SSL connections

### 4. Testing Connection
After configuration:
1. Start the external server
2. Test connection from client
3. Verify gRPC communication works

## Security Considerations
- Use strong authentication
- Implement rate limiting
- Monitor connection logs
- Regular security updates

## Troubleshooting
- Check firewall settings
- Verify server is running
- Check network connectivity
- Review server logs for errors
