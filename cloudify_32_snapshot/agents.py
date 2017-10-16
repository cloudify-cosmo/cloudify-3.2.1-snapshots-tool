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


import copy
import sys
import json

from cloudify_cli import utils as cli_utils

_BROKER_CREDENTIALS = {
    '3.2.1': {
        'broker_user': 'cloudify',
        'broker_pass': 'c10udify'
    },
    '3.2': {
        'broker_user': 'guest',
        'broker_pass': 'guest'
    }
}


def _is_compute(node):
    return 'cloudify.nodes.Compute' in node.type_hierarchy


def _is_windows(node):
    return 'cloudify.openstack.nodes.WindowsServer' in node.type_hierarchy


def _get_rest_client():
    management_ip = cli_utils.get_management_server_ip()
    return cli_utils.get_rest_client(management_ip)


def _get_node_instance_agent(node_instance, node, bootstrap_agent,
                             manager_ip, version, new_manager_ip):
    result = {}
    if node_instance.state != 'started':
        return result
    agent = copy.deepcopy(bootstrap_agent)
    node_properties = node.properties
    node_agent = node_properties.get('cloudify_agent', {})
    agent.update(node_agent)
    for key in ['user', 'password']:
        if key in agent:
            result[key] = agent[key]
    result['name'] = node_instance.id + '_342'
    result['queue'] = node_instance.id
    if 'ip' in node_instance.runtime_properties:
        result['ip'] = node_instance.runtime_properties['ip']
    elif 'ip' in node_properties:
        result['ip'] = node_properties['ip']
    result['manager_ip'] = manager_ip if new_manager_ip is None else new_manager_ip
    result['windows'] = _is_windows(node)
    result['version'] = version
    broker_config = {
        'broker_ip': manager_ip,
        'broker_ssl_enabled': False,
        'broker_ssl_cert': ''
    }
    broker_config.update(_BROKER_CREDENTIALS[version])
    result.update(broker_config)
    return result


def get_agents(client=None, manager_ip=None, new_manager_ip=None):
    if client is None:
        client = _get_rest_client()
    if manager_ip is None:
        manager_ip = cli_utils.get_management_server_ip()
    mgr_version = client.manager.get_version()['version']
    version = next((v for v in ['3.2.1', '3.2'] if mgr_version.startswith(v)),
                   None)
    if version is None:
        raise RuntimeError('Unknown manager version {0}'.format(mgr_version))
    bootstrap_agent = client.manager.get_context().get('context', {}).get(
        'cloudify', {}).get('cloudify_agent', {})
    result = {}
    for deployment in client.deployments.list():
        deployment_result = {}
        for node in client.nodes.list(deployment_id=deployment.id):
            if _is_compute(node):
                node_result = {}
                for node_instance in client.node_instances.list(
                        deployment_id=deployment.id,
                        node_name=node.id):
                    node_result[node_instance.id] = _get_node_instance_agent(
                        node_instance,
                        node,
                        bootstrap_agent,
                        manager_ip,
                        version,
                        new_manager_ip)
                deployment_result[node.id] = node_result
        result[deployment.id] = deployment_result
    return result


def dump_agents(filepath, manager_ip, new_manager_ip=None):
    agents = get_agents(manager_ip=manager_ip, new_manager_ip=new_manager_ip)
    with open(filepath, 'w') as out:
        out.write(json.dumps(agents))


def main(_):
    print json.dumps(get_agents(), indent=2)


if __name__ == '__main__':
    main(sys.argv)
