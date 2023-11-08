def support_ids(meta):
    if meta['name'].split()[-1] == 'create':
        return False
    id_parts = [param.get('id_part') for param in meta['parameters'] if param.get('id_part')]
    if 'name' not in id_parts and 'resource_name' not in id_parts:
        return False
    elif len(id_parts) > 0:
        return True
    return False
