# Security Policy

## Supported version

The default branch is the supported version of this academic project.

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could expose a camera,
network, credentials, or device control. Use GitHub's private security advisory
feature when it is available for this repository. Otherwise, contact the
maintainers privately through GitHub and include only the minimum information
needed to reproduce the issue.

## Sensitive data rules

Never commit or publish:

- Wi-Fi names, passwords, tokens, API keys, or `.env` files
- Local camera URLs, private network hosts, MAC addresses, or serial identifiers
- Model weights, captured images, videos, or personally identifying logs
- Browser screenshots that reveal private addresses or personal details

Use `CAMERA_HOST`, `COM_PORT`, and other neutral placeholders in documentation.
