"""
Tool for transforming a standard Kubernetes manifest file into a yRCA compatible one.
It does so by injecting the log analysis components into the input file.
"""

import argparse
import yaml
import json
from elasticsearch import Elasticsearch

YRCA_NAMESPACE = "yrca-deployment"


def import_yaml(input_file):
    """
    Import a YAML file and return its content as a dictionary.
    """
    with open(input_file, "r", encoding="utf-8") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return None


def parse_options():
    """
    Parse command line options.
    """
    parser = argparse.ArgumentParser(description="PROGETTO")
    parser.add_argument(
        "-i",
        "--inject",
        action="store_true",
        help="Inject log analysis components into the input file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output.yaml",
        help='Specify a custom output file pathname. Defaults to "output.yaml"',
    )
    parser.add_argument(
        "-t",
        "--timeout",
        default="1m",
        help="Specify a custom Envoy timeout. Defaults to 1m",
    )
    # parser.add_argument('input_file', metavar='input_file', help='Input file to be processed')
    parser.add_argument(
        "-c", "--connect", action="store_true", help="Connect to Elasticsearch instance"
    )
    parser.add_argument(
        "-es", "--es_host", default="localhost", help="Elasticsearch host", type=str
    )
    parser.add_argument(
        "-p", "--es_port", default=9200, help="Elasticsearch port", type=int
    )
    return parser.parse_args()


def load_manifests(filenames):
    """
    Load multiple manifest contents from a list of files.
    """
    return {filename: load_manifest(filename) for filename in filenames}


def load_manifest(filename):
    """
    Load manifest content from a file.
    """
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def build_merged_text(manifests):
    """
    Build merged text from list of manifest texts.
    """
    return "\n---\n".join(manifests) + "\n---\n"


def inject(yaml_file, timeout="1m", output_file="output.yaml"):
    """
    Inject log analysis components into a YAML file.
    """
    try:
        manifests = load_manifests(
            [
                yaml_file,
                "manifest/namespace_manifest.yaml",
                "manifest/istio_manifest.yaml",
                "manifest/elk_manifest.yaml",
            ]
        )

        virtual_services = []
        docs_text = []

        for doc in yaml.safe_load_all(manifests[yaml_file]):
            if doc:
                doc = replace_namespace(doc)
                if doc["kind"].lower() == "service":
                    service_name = doc["metadata"]["name"]
                    virtual_service = create_virtual_service(service_name, timeout)
                    virtual_services.append(virtual_service)
                docs_text.append(yaml.dump(doc, default_flow_style=False))

        virtual_services_text = [
            yaml.dump(vs, default_flow_style=False) for vs in virtual_services
        ]
        merged_text = build_merged_text(
            [
                manifests["manifest/istio_manifest.yaml"],
                manifests["manifest/elk_manifest.yaml"],
                manifests["manifest/namespace_manifest.yaml"],
            ]
            + docs_text
            + virtual_services_text
        )

        with open(output_file, "w", encoding="utf-8") as stream:
            stream.write(merged_text)
            print(f"Output file written to {output_file}")

    except FileNotFoundError as exc:
        print(exc)


def replace_namespace(yaml_section):
    """
    Replace or set the namespace in the YAML section.
    """
    if "metadata" not in yaml_section:
        yaml_section["metadata"] = {}
    yaml_section["metadata"]["namespace"] = YRCA_NAMESPACE
    return yaml_section


def create_virtual_service(service_name, timeout):
    """
    Create an Istio VirtualService configuration for a given service.
    """
    return {
        "apiVersion": "networking.istio.io/v1alpha3",
        "kind": "VirtualService",
        "metadata": {"name": service_name, "namespace": YRCA_NAMESPACE},
        "spec": {
            "hosts": [service_name],
            "http": [
                {"route": [{"destination": {"host": service_name}}], "timeout": timeout}
            ],
        },
    }


def get_istio_logs(es_host="localhost", es_port=9200):
    # Connect to the Elasticsearch instance
    try:
        es = Elasticsearch([{"host": es_host, "port": es_port, "scheme": "http"}])
    except Exception as exc:
        print(exc)
        return

    # Define the query
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"kubernetes.namespace.keyword": "yrca-deployment"}},
                    {"match": {"kubernetes.container.name": "istio-proxy"}},
                ]
            }
        }
    }

    # Execute the query and get the results
    response = es.search(index="logstash-gelf-*", body=query)

    # Extract logs from the response
    logs = [hit["_source"] for hit in response["hits"]["hits"]]

    for log in logs:
        print(json.dumps(log, indent=4))


def main():
    """
    Main function to execute script.
    """
    args = parse_options()
    if args.inject:
        inject(args.input_file, args.timeout, args.output)
    if args.connect:
        get_istio_logs(args.es_host, args.es_port)


if __name__ == "__main__":
    main()
