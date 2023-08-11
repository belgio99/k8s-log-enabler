import yaml, sys, argparse

def main():
    args = parse_options()
    if args.inject:
        inject(args.input_file, args.output)

def parse_options():
    parser = argparse.ArgumentParser(description='PROGETTO')
    parser.add_argument('-i', '--inject', action='store_true', help='Injects the input file with the log analysis components')
    #parser.add_argument('--analyzeLogs', action='store_true', help='Analyze the logs and creates yRCA compatible log file')
    parser.add_argument('-o', '--output', default='output.yaml', help='Specify a custom output file pathname. If not specified, the output file will be named "output.yaml"')
    parser.add_argument('input_file', metavar='input_file', help='The input file to be processed')
    return parser.parse_args()

def inject(yamlFile, outputFile="output.yaml"):
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

    for yaml_section in yaml.safe_load_all(input_file):
        if yaml_section is not None:
            yaml_section = replace_namespace(yaml_section)

            merged_text += yaml.dump(yaml_section, default_flow_style=False)
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
    yaml_section['metadata']['namespace'] = "yrca-deployment"
    return yaml_section

if __name__ == "__main__":
    main()