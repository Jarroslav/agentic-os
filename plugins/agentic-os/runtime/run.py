#!/usr/bin/env python3
"""Read one versioned JSON request; emit one JSON result without repository writes."""
import json
import sys

from agentic_runtime.contracts import load_registry, resolve_policy, normalize_input, validate_transition, retry_allowed, lookup_contract


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field: " + key)
        result[key] = value
    return result


def main():
    try:
        request = json.load(sys.stdin, object_pairs_hook=unique_object)
        if not isinstance(request, dict) or request.get('api_version') != '1.0.0':
            raise ValueError('unsupported api_version')
        operation = request.get('operation')
        fields = {'registry.get': ({'api_version', 'operation'}, set()),
                  'policy.resolve': ({'api_version', 'operation', 'entrypoint'}, {'overrides'}),
                  'contract.lookup': ({'api_version', 'operation', 'section', 'identifier'}, set()),
                  'input.normalize': ({'api_version', 'operation', 'payload'}, {'legacy'}),
                  'transition.validate': ({'api_version', 'operation', 'source', 'target'}, set()),
                  'retry.allowed': ({'api_version', 'operation', 'loop_id', 'attempts_used'}, set())}
        if not isinstance(operation, str) or operation not in fields:
            raise ValueError('unknown operation')
        required, optional = fields[operation]
        if not required <= set(request) or set(request) - required - optional:
            raise ValueError('unknown or missing request fields')
        if operation == 'registry.get':
            value = load_registry()
        elif operation == 'policy.resolve':
            value = resolve_policy(request['entrypoint'], request.get('overrides'))
        elif operation == 'contract.lookup':
            value = lookup_contract(request['section'], request['identifier'])
        elif operation == 'input.normalize':
            value = normalize_input(request['payload'], request.get('legacy', False))
        elif operation == 'transition.validate':
            value = validate_transition(request['source'], request['target'])
        else:
            value = retry_allowed(request['loop_id'], request['attempts_used'])
        result = {'api_version': '1.0.0', 'ok': True, 'result': value}
        status = 0
    except (ValueError, TypeError, KeyError) as error:
        result = {'api_version': '1.0.0', 'ok': False,
                  'error': {'code': 'invalid_request', 'message': str(error)}}
        status = 2
    print(json.dumps(result, sort_keys=True))
    return status


if __name__ == '__main__':
    sys.exit(main())
