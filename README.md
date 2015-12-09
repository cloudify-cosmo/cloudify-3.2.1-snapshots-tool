# Create a snapshot on a 3.2.1 manager

A tool for creating snapshots for Cloudify 3.2.1 managers.

This repository has been created to make creating snapshots on a Cloudify 3.2.1 manager possible - this feature has been introduced in the 3.3 version.
This package should be installed in virtual environment where cloudify CLI is installed. After installation new command should be available: cfy-snapshot32.
To create a snapshot, one needs to be in the directory where the CLI used for the 3.2.1 manager has been initialized. This directory should have a `.cloudify` directory inside.
All that is left is running the command in the following way:

`cfy-snapshot32`

After the command finishes, there should be a snapshot.zip file in the current directory.

Parameters and flags:

    --include-metrics
        Include InfluxDB metrics in the snapshot

    -o, --output-file
        The created snapshot's file, snapshot.zip by default

Following parameters should be set if manager was bootstrapped with those parameters changed:

    --fs-root FILE_SERVER_ROOT
        Path to file server root in manager

    --fs-blueprints FILE_SERVER_BLUEPRINTS_FOLDER
        Name of blueprints folder inside file server

    --fs-ublueprints FILE_SERVER_UPLOADED_BLUEPRINTS_FOLDER
        Name of uploaded blueprints folder inside file server
