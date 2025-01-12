import hashlib

def hash_row(row):
    row_str = row.to_string()
    hash_object = hashlib.sha256()
    hash_object.update(row_str.encode())
    hash_hex = hash_object.hexdigest()
    return hash_hex
