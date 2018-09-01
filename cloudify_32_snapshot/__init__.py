########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


import argparse
import subprocess
import json
import os
import zipfile
import tempfile


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
    parser.add_argument('--manager-321-home-folder',
                        dest='manager_321_home_folder')

    parser.add_argument('--manager-342-ip',
                        dest='manager_342_ip')
    parser.add_argument('--manager-321-ip',
                        dest='manager_321_ip')
    parser.add_argument('--manager-321-user',
                        dest='manager_321_user')
    parser.add_argument('--manager-321-key',
                        dest='manager_321_key')
    parser.add_argument('--chunk-size',
                        dest='chunk_size',
                        type=int,
                        default=1000)
    parser.add_argument('--remote-output',
                        dest='remote_output',
                        required=True,
                        help="Location, inside the docker container, where the snapshot should be stored")
    parser.add_argument('--remote-temp-dir',
                        dest='remote_temp_dir',
                        default=None)
    parser.add_argument('--remote-output-host',
                        dest='remote_output_host',
                        required=True,
                        help="Location to download the snapshot from; this is the 'host' view of the value "
                             "provided by the '--remote-output' parameter")

    pargs = parser.parse_args()

    wargs = ' '.join([
        '--fs-root ' + pargs.file_server_root,
        '--fs-blueprints ' + pargs.file_server_blueprints_folder,
        '--fs-ublueprints ' + pargs.file_server_uploaded_blueprints_folder,
        '--manager-ip ' + pargs.manager_321_ip,
        '--chunk-size ' + str(pargs.chunk_size),
        '--output ' + pargs.remote_output
    ])
    if pargs.remote_temp_dir:
        wargs += ' --temp-dir {}'.format(pargs.remote_temp_dir)
    if pargs.include_metrics:
        wargs += ' --include-metrics'

    driver(pargs.output_file,
           wargs,
           pargs.manager_321_ip,
           pargs.manager_321_user,
           pargs.manager_321_key,
           pargs.manager_342_ip,
           pargs.manager_321_home_folder,
           pargs.remote_output_host)


def driver(output_path,
           worker_args,
           old_manager_ip,
           old_manager_user,
           old_manager_key,
           new_manager_ip,
           old_manager_home_folder,
           remote_output_host):
    script_path = os.path.join(
        os.path.dirname(__file__),
        'create_snapshot_3_2.py'
    )

    def _call(cmd):
        print "Executing: {}".format(cmd)
        subprocess.check_output(cmd)

    tmp_script_location = '/tmp/script.py'
    _call(['scp', '-i', old_manager_key, script_path,
           "%s@%s:%s" % (old_manager_user, old_manager_ip, tmp_script_location)])
    _call(['ssh', '-i', old_manager_key, "%s@%s" % (old_manager_user, old_manager_ip),
           'sudo', 'mv', tmp_script_location, '%s/script.py' % old_manager_home_folder])
    _call(['ssh', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3',
           '-i', old_manager_key, "%s@%s" % (old_manager_user, old_manager_ip),
           'sudo', 'docker', 'exec', 'cfy', '/bin/bash', '-c',
           '"python -u /tmp/home/script.py {0}"'.format(worker_args)])
    _call(['scp', '-i', old_manager_key,
           "%s@%s:%s" % (old_manager_user, old_manager_ip, remote_output_host),
           output_path])
    _call(['ssh', '-i', old_manager_key, "%s@%s" % (old_manager_user, old_manager_ip),
           'sudo', 'rm', '-f', remote_output_host, '%s/script.py' % old_manager_home_folder])

    with zipfile.ZipFile(output_path, 'r',  allowZip64=True) as archive:
        manager = json.loads(archive.open(MANAGER_FILE).read())
        manager_ip = manager[MANAGER_IP_KEY]
    import agents
    _, agents_path = tempfile.mkstemp()
    agents.dump_agents(agents_path, manager_ip, new_manager_ip)
    with zipfile.ZipFile(output_path, 'a',  allowZip64=True) as archive:
        archive.write(agents_path, AGENTS_FILE)
