# Security Policy

## Supported versions

Security fixes are made on the latest released version. During the alpha period, older
versions are not guaranteed to receive backports.

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could enable unauthorized CAN
transmission, unsafe replay, code execution, path traversal or disclosure of captures.
Use GitHub's private vulnerability reporting feature when it is enabled. Otherwise,
contact the repository owner privately using the address listed on their GitHub profile.

Include the affected version, operating system, reproduction steps, impact and any safe
mitigation. Do not include confidential DBC files or real vehicle captures. Maintainers
should acknowledge a report within seven days and will coordinate disclosure after a fix
is available.

## Operational safety

OCA is a development and educational tool, not a safety-certified diagnostic product.
Receiving is not necessarily passive unless the hardware is in listen-only mode. TX,
automatic responses and replay can actuate devices. Use an isolated, correctly terminated
bench network and obtain authorization before connecting to any vehicle or machine.
