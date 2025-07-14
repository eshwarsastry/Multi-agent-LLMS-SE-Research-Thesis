# SSL Certificates Setup

This directory is for storing SSL certificates used by the application.

## Setup Instructions:

1. **Place your certificate file** in this directory (e.g., `custom_ca.pem`)
2. **Update your `.env` file** with the correct path:
   ```
   REQUESTS_CA_BUNDLE=./certs/custom_ca.pem
   ```

## Security Notes:

- **Never commit certificates to Git** - they are automatically ignored
- **Keep certificates secure** - they contain sensitive information
- **Use different certificates** for different environments (dev/staging/prod)

## File Types Supported:

- `.pem` - PEM format certificates
- `.crt` - Certificate files
- `.key` - Private key files
- `.p12` - PKCS#12 format
- `.pfx` - Personal Information Exchange format

## Example Certificate Structure:

```
certs/
├── custom_ca.pem          # Your custom CA certificate
├── client_cert.pem        # Client certificate (if needed)
└── README.md              # This file
``` 