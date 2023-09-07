"""
Tool for extending a standard Kubernetes manifest file into a manifest with logging capabilities.
It does so by injecting the log analysis components into the input file.
"""

import argparse
import yaml
from elasticsearch import Elasticsearch
from yrca import yrca_process_logs

LOG_NAMESPACE = "log-enabled"


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
        metavar="input_file",
        help="Inject log analysis components into the specified input file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output",
        help='Specify a custom output file pathname. Defaults to "output"',
    )
    parser.add_argument(
        "-t",
        "--timeout",
        default="1m",
        help="Specify a custom Envoy timeout. Defaults to 1m",
    )
    parser.add_argument(
        "-c", "--connect", help="Connect to the specified Elasticsearch instance", type=str
    )
    parser.add_argument(
        "-p", "--port", default=9200, help="Elasticsearch port", type=int
    )
    parser.add_argument(
        "--dump-all", help="Dump all the logs in the Elasticsearch instance (to a file, if used with -o). Cannot be used with yRCA log output format.", type=str)
    parser.add_argument(
        "-f", "--format", choices=['yrca', 'gelf', 'syslog'], default='yrca', help="Specify the format of the logs to be processed. Defaults to yrca."
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
    yaml_section["metadata"]["namespace"] = LOG_NAMESPACE
    return yaml_section


def create_virtual_service(service_name, timeout):
    """
    Create an Istio VirtualService configuration for a given service.
    """
    return {
        "apiVersion": "networking.istio.io/v1alpha3",
        "kind": "VirtualService",
        "metadata": {"name": service_name, "namespace": LOG_NAMESPACE},
        "spec": {
            "exportTo": ["."],
            "hosts": [service_name],
            "http": [
                {"route": [{"destination": {"host": service_name}}], "timeout": timeout}
            ],
        },
    }


def get_istio_logs(es_host="localhost", port=9200, output_file=None, dump_all=False, format="yrca"):

    if format == "yrca" & dump_all:
        print("yRCA only requires the dump of Envoy proxies, so it cannot be used with --dump-all")
        return None
    # Connect to the Elasticsearch instance
    es = Elasticsearch([{"host": es_host, "port": port, "scheme": "http"}])
    size = 10000

    # Define the query
    query = {
        "bool": {
                "must": [
                    {"match": {"kubernetes.namespace": "log-enabled"}},
                    {"match": {"kubernetes.container.name": "istio-proxy"}},
                    {"match": {"message": "start_time"}}
                ]
            }
        }
    if dump_all:
        query = {
            "bool": {
                    "must": [
                        {"match": {"kubernetes.namespace": "log-enabled"}},
                    ]
                }
            }
    try:
        response = es.search(index="filebeat-*", query=query, size=size, sort="@timestamp:asc")
    except Exception as e:
        print("Error while connecting to Elasticsearch instance")
        print(e)
        return None
    

    logs = []
    if format == "yrca":
    # Extract logs from the response
        for hit in response["hits"]["hits"]:
            pod_name = hit["_source"]["kubernetes"]["pod"]["name"]
            log_message = hit["_source"]["message"]
            formatted_log = f"{pod_name} {log_message}"
            logs.append(formatted_log)

        logs = yrca_process_logs(logs)

    elif format == "gelf":
        for hit in response["hits"]["hits"]:
            version = "1.1"
            host = hit["_source"]["host"]["name"]
            short_message = hit["_source"]["message"].split("\n")[0]  # Assuming first line is short message
            full_message = hit["_source"]["message"]
            timestamp = hit["_source"]["@timestamp"]
            level = "INFO"  # This may need to be converted into GELF level

            formatted_log = f"version: {version}, host: {host}, short_message: {short_message}, full_message: {full_message}, timestamp: {timestamp}, level: {level}"
            logs.append(formatted_log)

    elif format == "syslog":
        for hit in response["hits"]["hits"]:
            priority = "<134>"  # Sample priority, this can vary based on severity and facility
            timestamp = hit["_source"]["@timestamp"]
            hostname = hit["_source"]["host"]["name"]
            app_name = hit["_source"]["kubernetes"]["container"]["name"]
            procid = hit["_source"]["kubernetes"]["pod"]["name"]
            msgid = "-"  # Placeholder, you might want to replace it with a proper ID if available
            structured_data = "-"  # Placeholder, replace if you have structured data
            msg = hit["_source"]["message"]

            formatted_log = f"{priority}{timestamp} {hostname} {app_name} {procid} {msgid} {structured_data} {msg}"
            logs.append(formatted_log)


    if output_file:
        with open(output_file, "w", encoding="utf-8") as stream:
            stream.write("\n".join(logs))
            print(f"Output file written to {output_file}")
    else:
        print("\n".join(logs))

def main():
    """
    Main function to execute script.
    """
    args = parse_options()
    if args.inject:
        inject(args.inject, args.timeout, args.output)
    if args.connect:
        get_istio_logs(args.connect, args.port, args.output, args.dump_all, args.format)

        


if __name__ == "__main__":
    main()
