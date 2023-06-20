import yaml, sys, argparse

def import_yaml(input_file):
    with open(input_file, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


def parse_options():
    parser = argparse.ArgumentParser(description='PROGETTO')
    parser.add_argument('--inject', action='store_true', help='Injects the input file with the log analysis components')
    #parser.add_argument('--analyzeLogs', action='store_true', help='Analyze the logs and creates yRCA compatible log file')
    parser.add_argument('-n', '--namespace', help='If you want to force a custom injection namespace, enter its name here. Otherwise, it will be auto parsed from the input file. You can specify multiple namespaces by separating them with a comma (e.g. "namespace1,namespace2")')
    parser.add_argument('-o', '--output', help='Specify a custom output file pathname. If not specified, the output file will be named "output.yaml"')
    parser.add_argument('input_file', metavar='input_file', help='The input file to be processed')
    return parser.parse_args()


def auto_parse_namespace(yaml_input_file):
    namespaces = []
    for yaml_input in yaml.safe_load_all(yaml_input_file):
        try:
            namespace = yaml_input['metadata']['namespace']
            print(f'Auto parsed namespace: {namespace}')
            namespaces.append(namespace)
        except Exception as exc:
            continue
    return namespaces


def inject(yamlFile,input_namespaces, outputFile='output.yaml'):
    input_file = open(yamlFile, 'r')
    if not input_namespaces:
        namespaces = auto_parse_namespace(input_file)
    else:
        namespaces = input_namespaces.split(',')
        
    
    try:
        namespace_template = import_yaml('namespace_template.yaml')
    except Exception as exc:
        print(exc)
        sys.exit(1)
    
    if not namespace_template:
        print('Error while parsing the namespace template file')
        sys.exit(1)

    if not namespaces:
        print('No explicit namespaces found or specified. Will inject the default namespace')
        namespaces = ['default']
    
    namespace_text = ''
    for namespace in namespaces:
        new_namespace = namespace_template.copy()
        new_namespace['metadata']['name'] = namespace
        namespace_text += f"\n---\n{yaml.dump(new_namespace, default_flow_style=False)}"




    istio_file = open('istio_manifest.yaml', 'r')
    istio_text = istio_file.read()
    istio_file.close()

    input_file.seek(0)
    input_text = input_file.read()
    input_file.close()

    merged_text = f"{istio_text}{namespace_text}---\n{input_text}"

    with open(outputFile, 'w') as stream:
        try:
            stream.write(merged_text)
            print(f'Output file written to {outputFile}')
        except Exception as exc:
            print(exc)



def main():
    args = parse_options()
    if args.inject:
        inject(args.input_file, args.namespace)


if __name__ == "__main__":
    main()