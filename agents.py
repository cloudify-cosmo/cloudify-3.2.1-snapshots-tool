import copy
import sys
import json

from cloudify_cli import utils as cli_utils

_BROKER_URL_FORMATS = {
    '3.2.1': 'amqp://cloudify:c10udify@{0}:5672//',
    '3.2': 'amqp://guest:guest@{0}:5672//'
}


def _is_compute(node):
    return 'cloudify.nodes.Compute' in node.type_hierarchy


def _is_windows(node):
    return 'cloudify.openstack.nodes.WindowsServer' in node.type_hierarchy


def _get_rest_client():
    management_ip = cli_utils.get_management_server_ip()
    return cli_utils.get_rest_client(management_ip)


def _get_node_instance_agent(node_instance, node, bootstrap_agent,
                             manager_ip, version, broker_url):
    result = {}
    agent = copy.deepcopy(bootstrap_agent)
    node_properties = node.properties
    node_agent = node_properties.get('cloudify_agent', {})
    agent.update(node_agent)
    for key in ['user', 'password']:
        if key in agent:
            result[key] = agent[key]
    result['name'] = node_instance.id
    result['queue'] = node_instance.id
    if 'ip' in node_instance.runtime_properties:
        result['ip'] = node_instance.runtime_properties['ip']
    elif 'ip' in node_properties:
        result['ip'] = node_properties['ip']
    result['manager_ip'] = manager_ip
    result['windows'] = _is_windows(node)
    result['broker_url'] = broker_url
    result['version'] = version
    return result


def get_agents(client=None, manager_ip=None):
    if client is None:
        client = _get_rest_client()
    if manager_ip is None:
        manager_ip = cli_utils.get_management_server_ip()
    mgr_version = client.manager.get_version()['version']
    version = next((v for v in ['3.2.1', '3.2'] if mgr_version.startswith(v)),
                   None)
    if version is None:
        raise RuntimeError('Unknown manager version {0}'.format(mgr_version))
    broker_url = _BROKER_URL_FORMATS[version].format(manager_ip)
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
                        broker_url)
                deployment_result[node.id] = node_result
        result[deployment.id] = deployment_result
    return result


def dump_agents(filepath, manager_ip):
    agents = get_agents(manager_ip=manager_ip)
    with open(filepath, 'w') as out:
        out.write(json.dumps(agents))


def main(_):
    print json.dumps(get_agents(), indent=2)


if __name__ == '__main__':
    main(sys.argv)
