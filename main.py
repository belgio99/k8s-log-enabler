import yaml, sys, argparse

def import_yaml(input_file):
    with open(input_file, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


def parse_options():
    parser = argparse.ArgumentParser(description='PROGETTO')
    parser.add_argument('-i', '--inject', action='store_true', help='Injects the input file with the log analysis components')
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


def inject(yamlFile,input_namespaces, outputFile):
    input_file = open(yamlFile, 'r')
  # if not input_namespaces:
  #     namespaces = auto_parse_namespace(input_file)
  # else:
  #     namespaces = input_namespaces.split(',')
    namespaces = []
    if not outputFile:
        outputFile = 'output.yaml'

    
        
    
    try:
        namespace_template = import_yaml('manifest/namespace_manifest.yaml')
    except Exception as exc:
        print(exc)
        sys.exit(1)
    
    if not namespace_template:
        print('Error while parsing the namespace template file')
        sys.exit(1)

    if not namespaces:
        print('No explicit namespaces found or specified. Will use the \'yrca\' namespace')
        namespaces = ['yrca-deployment']
    



    istio_file = open('manifest/istio_manifest.yaml', 'r')
    istio_text = istio_file.read()
    istio_file.close()

    elk_file = open('manifest/elk_manifest.yaml', 'r')
    elk_text = elk_file.read()
    elk_file.close()

    merged_text = f"{istio_text}\n---\n{elk_text}\n---\n{namespace_template}\n---\n"

    for yaml_section in yaml.safe_load_all(input_file):
        if yaml_section is not None:
            if 'metadata' in yaml_section and 'namespace' in yaml_section['metadata']:
                yaml_section['metadata']['namespace'] = "yrca-deployment"
            elif 'metadata' in yaml_section:
                yaml_section['metadata']['namespace'] = "yrca-deployment"
            else:
                yaml_section['metadata'] = {'namespace': "yrca-deployment"}
            merged_text += yaml.dump(yaml_section, default_flow_style=False)
            merged_text += '\n---\n\n'


    with open(outputFile, 'w') as stream:
        try:
            stream.write(merged_text)
            print(f'Output file written to {outputFile}')
        except Exception as exc:
            print(exc)



def main():
    args = parse_options()
    if args.inject:
        inject(args.input_file, args.namespace, args.output)


if __name__ == "__main__":
    main()