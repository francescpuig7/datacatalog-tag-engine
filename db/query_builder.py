import json


def dict_to_query(data):
    """ Return a format SQL dialect query string LIKE cols and values"""
    bool_types = ['create_policy_tags', 'tag_history', 'enabled', 'overwrite']
    integer_types = ['tasks_ran', 'task_count', 'tasks_running', 'tasks_success', 'tasks_failed', 'refresh_frequency']
    timestamp_types = ['start_time', 'creation_time', 'completion_time', 'next_run', 'end_time']
    jsonb_types = ['fields']
    no_varchar_keys = bool_types + integer_types + jsonb_types

    query_values = "("
    query_cols = "("
    for k, v in data.items():
        query_cols += k + ','
        if k in no_varchar_keys:
            if jsonb_types:
                query_values += f"'{json_to_str(v)}',"
            else:
                query_values += str(v).replace('True', 'true') + ','
        else:
            query_values += f"'{v}',"
    query_cols = query_cols[0:-1] + ')'
    query_values = query_values[0:-1] + ')'
    return query_cols, query_values


def json_to_str(data):
    """ Convert python object (list/dict) in
    format JSON and return string"""
    # Convert Python to JSON
    json_object = json.dumps(data)

    # Return str JSON object
    return str(json_object)
