import yaml, argparse

def import_yaml(yaml_file):
    with open(yaml_file, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

def main():
    args = parse_options()
    if args.logconfig:
        logconfig(args.logconfig, args.namespace)
    elif args.analyzeLogs:
        analyzeLogs()


def parse_options():
    parser = argparse.ArgumentParser(description='PROGETTO')
    parser.add_argument('--logconfig', help='Creates the modified k8s yaml file from the input file')
    parser.add_argument('--analyzeLogs', action='store_true', help='Analyze the logs and creates yRCA compatible log file')
    parser.add_argument('-ns', '--namespace', help='If your Deployment uses a custom namespace, enter its name here')
    return parser.parse_args()

    


def logconfig(yamlFile,namespace):
    namespace_yaml = import_yaml('namespace.yaml')
    if namespace: #if the user specified a namespace
        namespace_yaml['metadata']['name'] = namespace

    namespace_text = yaml.dump(namespace_yaml, default_flow_style=False)

    istio_file = open('istio_manifest.yaml', 'r')
    istio_text = istio_file.read()
    istio_file.close()

    input_file = open(yamlFile, 'r')
    input_text = input_file.read()
    input_file.close()

    merged_text = f"{istio_text}\n---\n{namespace_text}\n---\n{input_text}"

    with open('modified.yaml', 'w') as stream:
        try:
            stream.write(merged_text)
        except Exception as exc:
            print(exc)


if __name__ == "__main__":
    main()