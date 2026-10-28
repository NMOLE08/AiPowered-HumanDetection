# Privacy and Data Handling

Sentinel Vision is designed to run locally. The default dashboard binds only to
the local machine, and the application does not implement cloud storage,
analytics, user accounts, telemetry, or a database.

## Data handled during a session

- latest camera frame in process memory;
- latest detection boxes, count, and timing values;
- bounded in-memory activity events;
- optional current Arduino serial connection.

The project does not persist this session data by default.

## Responsible use

Camera systems can capture people. Follow your institution's policies, obtain
required consent, use appropriate signage, and comply with applicable law before
deploying the project outside a controlled academic demonstration.

Do not publish videos, photos, stream URLs, network details, device identifiers,
or logs that identify people. Refer to [SECURITY.md](../SECURITY.md) for the
repository's sensitive-data rules.
