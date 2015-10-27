# Create a snapshot on a 3.2.1 manager

This repository has been created to make creating snapshots on a Cloudify 3.2.1 manager possible - this feature has been introduced in the 3.3 version.
To create a snapshot, one needs to be in the directory where the CLI used for the 3.2.1 manager has been initialized. This directory should have a `.cloudify` directory inside.
Additionally, the virtual environment used for the CLI should be initialized. All that is left is running the script in the following way:

`python create_snapshot_3_2.py`

After the script finishes, there should be a snapshot.zip file in the current directory.

Parameters and flags:

    --include-metrics
        Include InfluxDB metrics in the snapshot

    --output-file
        The created snapshot's file, snapshot.zip by default
