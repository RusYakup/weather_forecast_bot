from prometheus_client import Counter
import socket


def get_instance_id():
    return socket.gethostname()


instance_id = get_instance_id()


async def inc_counters() -> None:
    unknown_command_counter.labels(instance=instance_id).inc(0)
    count_instance_errors.labels(instance=instance_id).inc(0)
    count_user_errors.labels(instance=instance_id).inc(0)
    database_errors_counters[0].labels(instance=instance_id).inc(0)
    database_errors_counters[1].labels(instance=instance_id).inc(0)
    database_errors_counters[2].labels(instance=instance_id).inc(0)
    database_errors_counters[3].labels(instance=instance_id).inc(0)
    validation_error.labels(instance=instance_id).inc(0)

    for status_code in [401, 403]:
        external_api_error.labels(instance=instance_id, status_code=status_code).inc(0)


database_errors_counters = [
    Counter('database_connection_errors', 'Database connection errors', ['instance']),
    Counter('database_query_errors', 'Database query errors', ['instance']),
    Counter('database_other_errors', 'Other database errors', ['instance']),
    Counter('data_base_runtime', 'Database runtime errors', ['instance'])
]
external_api_error = Counter('external_api_error', 'Count of errors', ['instance', 'status_code'])

validation_error = Counter('external_api_validation_errors', 'Count of validation errors from external API services',
                           ['instance'])

unknown_command_counter = Counter('unknown_commands', 'Count of unknown commands received',
                                  ['instance'])

count_instance_errors = Counter('instance_errors', 'Count of errors by instance', ['instance'])

count_user_errors = Counter('user_errors', 'User interaction errors', ['instance'])
