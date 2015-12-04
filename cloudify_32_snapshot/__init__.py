import argparse
import json
import os
import zipfile
import tempfile

from distutils import spawn
from subprocess import call

from create_snapshot_3_2 import MANAGER_FILE, MANAGER_IP_KEY

AGENTS_FILE = 'agents.json'


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--fs-root', dest='file_server_root',
                        default='/opt/manager/resources/')
    parser.add_argument('--fs-blueprints',
                        dest='file_server_blueprints_folder',
                        default='blueprints')
    parser.add_argument('--fs-ublueprints',
                        dest='file_server_uploaded_blueprints_folder',
                        default='uploaded-blueprints')
    parser.add_argument('-o, --output-file', dest='output_file',
                        default='snapshot.zip')
    parser.add_argument('--include-metrics',
                        dest='include_metrics',
                        action='store_true')
    pargs = parser.parse_args()

    wargs = ' '.join([
        '--fs-root ' + pargs.file_server_root,
        '--fs-blueprints ' + pargs.file_server_blueprints_folder,
        '--fs-ublueprints ' + pargs.file_server_uploaded_blueprints_folder
    ])
    if pargs.include_metrics:
        wargs = '{0} --include-metrics'.format(wargs)

    driver(pargs.output_file, wargs)


def driver(output_path, worker_args):
    script_path = os.path.join(
        os.path.dirname(__file__),
        'create_snapshot_3_2.py'
    )

    scp(script_path, '~/script.py', True)
    call(['cfy', 'ssh', '-c', '''\
sudo docker exec cfy /bin/bash -c \
'cd /tmp/home; python script.py {0}'\
'''.format(worker_args)])
    scp(output_path, '~/snapshot_3_2.zip', False)
    call(['cfy', 'ssh', '-c',
          'rm -f ~/snapshot_3_2.zip ~/script.py'])
    with zipfile.ZipFile(output_path, 'r') as archive:
        manager = json.loads(archive.open(MANAGER_FILE).read())
        manager_ip = manager[MANAGER_IP_KEY]
    import agents
    _, agents_path = tempfile.mkstemp()
    agents.dump_agents(agents_path, manager_ip)
    with zipfile.ZipFile(output_path, 'a') as archive:
        archive.write(agents_path, AGENTS_FILE)


def scp(local_path, path_on_manager, to_manager):
    from cloudify_cli.utils import get_management_user
    from cloudify_cli.utils import get_management_server_ip
    from cloudify_cli.utils import get_management_key

    scp_path = spawn.find_executable('scp')
    management_path = '{0}@{1}:{2}'.format(
        get_management_user(),
        get_management_server_ip(),
        path_on_manager
    )
    command = [scp_path, '-o', 'StrictHostKeyChecking=no',
               '-i', os.path.expanduser(get_management_key())]
    if to_manager:
        command += [local_path, management_path]
    else:
        command += [management_path, local_path]
    rc = call(command)
    if rc:
        raise RuntimeError('Scp failed with exit code: {0}'.format(rc))
