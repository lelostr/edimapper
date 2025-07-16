import yaml
import json
from collections import defaultdict

def set_nested(d, path, value):
    parts = path.split('.')
    current = d

    for i, part in enumerate(parts):
        is_list = part.endswith('[]')
        key = part.replace('[]', '')

        if is_list:
            if key not in current:
                current[key] = []
            if i == len(parts) - 1:
                current[key].append(value)
            else:
                if not current[key] or not isinstance(current[key][-1], dict):
                    current[key].append({})
                current = current[key][-1]
        else:
            if i == len(parts) - 1:
                current[key] = value
            else:
                if key not in current:
                    current[key] = {}
                current = current[key]

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def normalize_registers(mapping):
    for field in mapping['fields'].values():
        field['register'] = str(field['register'])
    mapping['registers'] = {str(k): v for k, v in mapping['registers'].items()}

def load_edi(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [line.rstrip('\n') for line in f]

def build_register_tree(register_map):
    children_map = defaultdict(list)
    for reg, props in register_map.items():
        father = props.get('father')
        if father:
            children_map[str(father)].append(str(reg))
    return children_map

def match_fields(fields, reg_type):
    return [(k, v) for k, v in fields.items() if str(v['register']) == str(reg_type)]

def extract_fields(line, matched_fields, base_path):
    data = {}
    for key, conf in matched_fields:
        start = conf['start'] - 1
        end = start + conf['positions']
        raw = line[start:end].strip()
        # value = int(raw) if conf.get('type') == 'number' else raw

        # remove prefixo do caminho base
        relative_key = key[len(base_path):].lstrip('.') if key.startswith(base_path) else key
        set_nested(data, relative_key, raw)
    return data

def parse_block(lines, i, reg, register_tree, fields, base_path):
    matched_fields = match_fields(fields, reg)
    result = extract_fields(lines[i], matched_fields, base_path)
    children_regs = register_tree.get(reg, [])

    i += 1
    while i < len(lines):
        child_line = lines[i]
        child_reg = child_line[:3].strip()

        if child_reg not in children_regs:
            break

        child_fields = match_fields(fields, child_reg)
        if not child_fields:
            i += 1
            continue

        child_key = child_fields[0][0]
        child_path = '.'.join(child_key.split('.')[:-1])
        relative_child_path = child_path[len(base_path):].lstrip('.') if child_path.startswith(base_path) else child_path

        child_result, i = parse_block(lines, i, child_reg, register_tree, fields, child_path)
        set_nested(result, relative_child_path, child_result)

    return result, i

def parse_edi(edi_lines, mapping):
    fields = mapping['fields']
    register_map = mapping['registers']
    register_tree = build_register_tree(register_map)

    result = {}
    i = 0
    while i < len(edi_lines):
        line = edi_lines[i]
        reg = line[:3].strip()

        if reg in register_map and not register_map[reg].get('father'):
            block_fields = match_fields(fields, reg)
            if not block_fields:
                i += 1
                continue

            base_path = '.'.join(block_fields[0][0].split('.')[:-1])
            block_result, next_i = parse_block(edi_lines, i, reg, register_tree, fields, base_path)

            # Junta no JSON principal
            if base_path:
                set_nested(result, base_path, block_result)
            else:
                result.update(block_result)

            i = next_i
        else:
            i += 1

    return result

# Caminhos dos arquivos
yaml_path = 'mapeamento.yaml'
edi_path = 'arquivo.edi'

if __name__ == "__main__":
    mapping = load_yaml(yaml_path)
    normalize_registers(mapping)
    edi_lines = load_edi(edi_path)

    parsed = parse_edi(edi_lines, mapping)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
