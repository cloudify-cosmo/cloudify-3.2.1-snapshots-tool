import copy
import sys
import json

from cloudify_cli import utils as cli_utils


def _is_compute(node):
    return 'cloudify.nodes.Compute' in node.type_hierarchy


def _get_rest_client():
    management_ip = cli_utils.get_management_server_ip()
    return cli_utils.get_rest_client(management_ip)


def _get_node_instance_agent(node_instance, node, bootstrap_agent):
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
    return result


def get_agents(client=None):
    if client is None:
        client = _get_rest_client()
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
                        bootstrap_agent)
                deployment_result[node.id] = node_result
        result[deployment.id] = deployment_result
    return result


def dump_agents(filepath):
    agents = get_agents()
    with open(filepath, 'w') as out:
        out.write(json.dumps(agents))


def main(_):
    print json.dumps(get_agents(), indent=2)


if __name__ == '__main__':
    main(sys.argv)
