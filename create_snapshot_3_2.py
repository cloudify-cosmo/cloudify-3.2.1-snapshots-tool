import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile

from os import path
from distutils import spawn
from subprocess import call
from subprocess import check_output

# ------------------ Constants ------------------------

CHUNK_SIZE = 100

_METADATA_FILE = 'metadata.json'
# metadata fields
_M_HAS_CLOUDIFY_EVENTS = 'has_cloudify_events'
_M_VERSION = 'snapshot_version'

VERSION = '3.2'
AGENTS_FILE = 'agents.json'
MANAGER_FILE = 'manager.json'
MANAGER_IP_KEY = 'MANAGEMENT_IP'
ELASTICSEARCH = 'es_data'
CRED_DIR = 'snapshot-credentials'
CRED_KEY_NAME = 'agent_key'
INFLUXDB = 'influxdb_data'
INFLUXDB_DUMP_CMD = ('curl -s -G "http://localhost:8086/db/cloudify/series'
                     '?u=root&p=root&chunked=true" --data-urlencode'
                     ' "q=select * from /.*/" > {0}')

DUMP_STORAGE_TEMPLATE = (
    'http://localhost:9200/'
    'cloudify_storage/'
    '_search?from={start}&size={size}')
DUMP_EVENTS_TEMPLATE = (
    'http://localhost:9200/'
    'cloudify_events/_search?from={start}&size={size}')


# ------------------ Elasticsearch ---------------------
def _get_chunk(cmd):
    return check_output(['curl', '-s', '-XGET', cmd], universal_newlines=True)


def _remove_newlines(s):
    return s.replace('\n', '').replace('\r', '')


def _convert_to_bulk(chunk):
    def patch_node(n):
        if n['_type'] == 'execution' and\
                'is_system_workflow' not in n['_source']:
            n['_source']['is_system_workflow'] = False
        return json.dumps(n)

    return '\n'.join([_remove_newlines(patch_node(n))
                      for n in chunk if n['_type'] != 'provider_context'])\
        + '\n'


def _append_to_file(f, js):
    f.write(_convert_to_bulk(js['hits']['hits']))


def _dump_chunks(f, template, save=False):
    cmd = template.format(start='0', size=str(CHUNK_SIZE))
    js = json.loads(_get_chunk(cmd))
    if save:
        data = js['hits']['hits']
    _append_to_file(f, js)
    total = int(js['hits']['total'])
    if total > CHUNK_SIZE:
        for i in xrange(CHUNK_SIZE, total, CHUNK_SIZE):
            cmd = template.format(
                    start=str(i),
                    size=str(CHUNK_SIZE))
            js = json.loads(_get_chunk(cmd))
            if save:
                data.extend(js['hits']['hits'])
            _append_to_file(f, js)

    if save:
        return data


def dump_elasticsearch(file_path):
    with open(file_path, 'w') as f:
        data = _dump_chunks(f, DUMP_STORAGE_TEMPLATE, save=True)
        _dump_chunks(f, DUMP_EVENTS_TEMPLATE)

    return data


# ------------------ Utils ---------------------
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


def get_json_objects(f):
    def chunks(g):
        ch = g.read(10000)
        yield ch
        while ch:
            ch = g.read(10000)
            yield ch

    s = ''
    decoder = json.JSONDecoder()
    for ch in chunks(f):
        s += ch
        try:
            while s:
                obj, idx = decoder.raw_decode(s)
                yield json.dumps(obj)
                s = s[idx:]
        except:
            pass


def copy_data(archive_root, config, to_archive=True):
    DATA_TO_COPY = [
        (config.file_server_blueprints_folder, 'blueprints'),
        (config.file_server_uploaded_blueprints_folder, 'uploaded-blueprints')
    ]

    # files with constant relative/absolute paths
    for (p1, p2) in DATA_TO_COPY:
        if p1[0] != '/':
            p1 = path.join(config.file_server_root, p1)
        if p2[0] != '/':
            p2 = path.join(archive_root, p2)
        if not to_archive:
            p1, p2 = p2, p1

        if not path.exists(p1):
            continue

        if path.isfile(p1):
            shutil.copy(p1, p2)
        else:
            if path.exists(p2):
                shutil.rmtree(p2, ignore_errors=True)
            shutil.copytree(p1, p2)


# ------------------ Main ---------------------
def worker(config):
    metadata = {}
    tempdir = tempfile.mkdtemp('-snapshot-data')
    # files/dirs copy
    copy_data(tempdir, config)

    # elasticsearch
    storage = dump_elasticsearch(path.join(tempdir, ELASTICSEARCH))
    metadata[_M_HAS_CLOUDIFY_EVENTS] = True
    # influxdb
    if config.include_metrics:
        influxdb_file = path.join(tempdir, INFLUXDB)
        influxdb_temp_file = influxdb_file + '.temp'
        call(INFLUXDB_DUMP_CMD.format(influxdb_temp_file), shell=True)
        with open(influxdb_temp_file, 'r') as f, open(influxdb_file, 'w') as g:
            for obj in get_json_objects(f):
                g.write(obj + '\n')

        os.remove(influxdb_temp_file)

    # credentials
    archive_cred_path = path.join(tempdir, CRED_DIR)
    os.makedirs(archive_cred_path)

    for n in filter(lambda x: x['_type'] == 'node', storage):
        props = n['_source']['properties']
        if 'cloudify_agent' in props and 'key' in props['cloudify_agent']:
            node_id = n['_id']
            agent_key_path = props['cloudify_agent']['key']
            os.makedirs(path.join(archive_cred_path, node_id))
            shutil.copy(path.expanduser(agent_key_path),
                        path.join(archive_cred_path, node_id, CRED_KEY_NAME))

    # version
    metadata[_M_VERSION] = VERSION

    manager = {
        MANAGER_IP_KEY: os.environ[MANAGER_IP_KEY]
    }
    with open(path.join(tempdir, MANAGER_FILE), 'w') as f:
        f.write(json.dumps(manager))

    # metadata
    with open(path.join(tempdir, _METADATA_FILE), 'w') as f:
        json.dump(metadata, f)

    # zip
    shutil.make_archive('/tmp/home/snapshot_3_2',
                        'zip',
                        tempdir)
    # end
    shutil.rmtree(tempdir)


def driver(output_path, worker_args):
    scp(sys.argv[0], '~/script.py', True)
    call(['cfy', 'ssh', '-c', '''\
sudo docker exec cfy /bin/bash -c \
'cd /tmp/home; python script.py --worker {0}'\
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', dest='is_worker', action='store_true')

    parser.add_argument('--fs-root', dest='file_server_root',
                        default='/opt/manager/resources/')
    parser.add_argument('--fs-blueprints',
                        dest='file_server_blueprints_folder',
                        default='blueprints')
    parser.add_argument('--fs-ublueprints',
                        dest='file_server_uploaded_blueprints_folder',
                        default='uploaded-blueprints')

    parser.add_argument('--output-file', dest='output_file',
                        default='snapshot.zip')

    parser.add_argument('--include-metrics',
                        dest='include_metrics',
                        action='store_true')
    pargs = parser.parse_args()

    if pargs.is_worker:
        # on docker
        worker(pargs)
    else:
        # on host
        wargs = ' '.join([
            '--fs-root ' + pargs.file_server_root,
            '--fs-blueprints ' + pargs.file_server_blueprints_folder,
            '--fs-ublueprints ' + pargs.file_server_uploaded_blueprints_folder
        ])
        if pargs.include_metrics:
            wargs = '{0} --include-metrics'.format(wargs)

        driver(pargs.output_file, wargs)


if __name__ == '__main__':
    main()
