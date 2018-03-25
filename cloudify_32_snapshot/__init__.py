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
import fabric.api
import fabric.operations
import json
import os
import zipfile
import tempfile


from create_snapshot_3_2 import MANAGER_FILE, MANAGER_IP_KEY

AGENTS_FILE = 'agents.json'


def main():
    try:
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

        pargs = parser.parse_args()

        wargs = ' '.join([
            '--fs-root ' + pargs.file_server_root,
            '--fs-blueprints ' + pargs.file_server_blueprints_folder,
            '--fs-ublueprints ' + pargs.file_server_uploaded_blueprints_folder,
            '--manager-ip ' + pargs.manager_321_ip
        ])
        if pargs.include_metrics:
            wargs = '{0} --include-metrics'.format(wargs)

        driver(pargs.output_file,
               wargs,
               pargs.manager_321_ip,
               pargs.manager_321_user,
               pargs.manager_321_key,
               pargs.manager_342_ip,
               pargs.manager_321_home_folder)
    except Exception as e:
        import traceback
        traceback.print_exc()


def driver(output_path,
           worker_args,
           old_manager_ip,
           old_manager_user,
           old_manager_key,
           new_manager_ip,
           old_manager_home_folder):
    script_path = os.path.join(
        os.path.dirname(__file__),
        'create_snapshot_3_2.py'
    )
    with fabric.api.settings(user=old_manager_user,
                             host_string=old_manager_ip,
                             key_filename=old_manager_key):
        fabric.operations.put(script_path,
                              '{0}/script.py'.format(old_manager_home_folder),
                              use_sudo=True)
        fabric.operations.run('sudo docker exec cfy '
                              '/bin/bash -c "python /tmp/home/script.py {0}"'.format(worker_args))
        fabric.operations.sudo('mv {0}/snapshot_3_2.zip /tmp/snapshot_3_2.zip'.format(old_manager_home_folder))
        fabric.operations.get('/tmp/snapshot_3_2.zip', output_path)
        fabric.operations.sudo('rm -f {0}/snapshot_3_2.zip '
                               '{0}/script.py'.format(old_manager_home_folder))

    with zipfile.ZipFile(output_path, 'r') as archive:
        manager = json.loads(archive.open(MANAGER_FILE).read())
        manager_ip = manager[MANAGER_IP_KEY]
    import agents
    _, agents_path = tempfile.mkstemp()
    agents.dump_agents(agents_path, manager_ip, new_manager_ip)
    with zipfile.ZipFile(output_path, 'a') as archive:
        archive.write(agents_path, AGENTS_FILE)
