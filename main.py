import yaml, sys, argparse

yrca_namespace = "yrca-deployment"

def main():
    args = parse_options()
    if args.inject:
        inject(args.input_file, args.timeout, args.output)

def parse_options():
    parser = argparse.ArgumentParser(description='PROGETTO')
    parser.add_argument('-i', '--inject', action='store_true', help='Injects the input file with the log analysis components')
    #parser.add_argument('--analyzeLogs', action='store_true', help='Analyze the logs and creates yRCA compatible log file')
    parser.add_argument('-o', '--output', default='output.yaml', help='Specify a custom output file pathname. If not specified, the output file will be named "output.yaml"')
    parser.add_argument('-t', '--timeout', default='1m', help='You can specify a custom Envoy timeout. If not specified, the default value is 1m')
    parser.add_argument('input_file', metavar='input_file', help='The input file to be processed')
    return parser.parse_args()

def inject(yamlFile, timeout="1m", outputFile="output.yaml"):
    try:
        input_file = open(yamlFile, 'r')
    except Exception as exc:
        print(exc)
        sys.exit(1)
    
    namespace_file = open('manifest/namespace_manifest.yaml', 'r')
    namespace_text = namespace_file.read()
    namespace_file.close()

    istio_file = open('manifest/istio_manifest.yaml', 'r')
    istio_text = istio_file.read()
    istio_file.close()

    elk_file = open('manifest/elk_manifest.yaml', 'r')
    elk_text = elk_file.read()
    elk_file.close()

    merged_text = f"{istio_text}\n---\n{elk_text}\n---\n{namespace_text}\n---\n"

    virtual_services = []

    for doc in yaml.safe_load_all(input_file):
        if doc is not None:
            doc = replace_namespace(doc)
            if doc["kind"].lower() == "service":
                service_name = doc["metadata"]["name"]
                vs = create_virtual_service(service_name, timeout)
                virtual_services.append(vs)
            merged_text += yaml.dump(doc, default_flow_style=False)
            merged_text += '\n---\n\n'

    for vs in virtual_services:
        merged_text += yaml.dump(vs, default_flow_style=False)
        merged_text += '\n---\n\n'

    with open(outputFile, 'w') as stream:
        try:
            stream.write(merged_text)
            print(f'Output file written to {outputFile}')
        except Exception as exc:
            print(exc)

def replace_namespace(yaml_section):
    if 'metadata' not in yaml_section:
        yaml_section['metadata'] = {}
    yaml_section['metadata']['namespace'] = yrca_namespace
    return yaml_section

def create_virtual_service(service_name, timeout):
    """
    Create an Istio VirtualService configuration for the given service.
    """
    return {
        "apiVersion": "networking.istio.io/v1alpha3",
        "kind": "VirtualService",
        "metadata": {
            "name": service_name,
            "namespace": yrca_namespace
        },
        "spec": {
            "hosts": [service_name],
            "http": [{
                "route": [{
                    "destination": {
                        "host": service_name
                    }
                }],
                "timeout": timeout
            }]
        }
    }


if __name__ == "__main__":
    main()