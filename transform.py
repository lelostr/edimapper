import yaml
import json

def load_yaml(yaml_path):
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

def load_edi(edi_path):
    with open(edi_path, 'r', encoding='utf-8') as f:
        return [line.rstrip('\n') for line in f]

# Função para setar valor aninhado em dict usando dot notation
def set_nested_value(d, key_path, value):
    keys = key_path.split('.')
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value

def parse_edi(edi_lines, mapping):
    result = {}
    fields = mapping['fields']

    for key, field in fields.items():
        reg_code = str(field['register']).zfill(3)
        start = int(field['start']) - 1
        end = start + int(field['positions'])

        line = next((l for l in edi_lines if l.startswith(reg_code)), None)
        if line:
            value = line[start:end].strip()
            if field.get('type') == 'number':
                try:
                    value = int(value)
                except ValueError:
                    pass
            set_nested_value(result, key, value)
        else:
            set_nested_value(result, key, None)

    return result

# Caminhos dos arquivos
yaml_path = './samples/map_notfis.yaml'
edi_path = './samples/notfis.txt'

if __name__ == "__main__":
    mapping = load_yaml(yaml_path)
    edi_lines = load_edi(edi_path)
    data = parse_edi(edi_lines, mapping)
    print(json.dumps(data, indent=2, ensure_ascii=False))
