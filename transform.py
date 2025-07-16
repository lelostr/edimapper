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

def load_edi(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [line.rstrip('\n') for line in f]

def build_register_tree(register_map):
    children_map = defaultdict(list)
    for reg, props in register_map.items():
        father = props.get('father')
        if father:
            children_map[father].append(reg)
    return children_map

def match_fields(fields, reg_type):
    return [(k, v) for k, v in fields.items() if str(v['register']) == str(reg_type)]

def extract_fields(line, matched_fields):
    data = {}
    for key, conf in matched_fields:
        start = conf['start'] - 1
        end = start + conf['positions']
        raw = line[start:end].strip()
        # value = int(raw) if conf.get('type') == 'number' else raw
        set_nested(data, key, raw)
    return data

def parse_block(lines, i, reg, register_tree, fields):
    matched_fields = match_fields(fields, reg)
    result = extract_fields(lines[i], matched_fields)
    children_regs = register_tree.get(reg, [])

    i += 1
    while i < len(lines):
        child_line = lines[i]
        child_reg = child_line[:3]

        if child_reg not in children_regs:
            break

        child_result, i = parse_block(lines, i, child_reg, register_tree, fields)

        # Descobre o ponto de inserção via campos filhos
        for key, conf in fields.items():
            if str(conf['register']) == child_reg:
                path = '.'.join(key.split('.')[:-1])
                if '[]' in key:
                    path += '[]'
                    set_nested(result, path, child_result)
                else:
                    set_nested(result, path, child_result)
                break

    return result, i

def parse_edi(edi_lines, mapping):
    fields = mapping['fields']
    register_map = mapping.get('registers', {})
    register_tree = build_register_tree(register_map)

    result = {}
    i = 0
    while i < len(edi_lines):
        line = edi_lines[i]
        reg = line[:3].strip()

        if reg in register_map and not register_map[reg].get('father'):  # topo da hierarquia
            block_result, next_i = parse_block(edi_lines, i, reg, register_tree, fields)

            for key in block_result:
                if key in result and isinstance(result[key], list):
                    result[key].append(block_result[key])
                elif key in result and isinstance(result[key], dict):
                    # já existe, transforma em lista
                    result[key] = [result[key], block_result[key]]
                else:
                    result[key] = block_result[key]

            i = next_i
        else:
            i += 1

    return result

# Arquivos de entrada
yaml_path = 'mapeamento.yaml'
edi_path = 'arquivo.edi'

if __name__ == "__main__":
    mapping = load_yaml(yaml_path)
    edi_lines = load_edi(edi_path)
    parsed = parse_edi(edi_lines, mapping)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
