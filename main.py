"""
Tool for extending a standard Kubernetes manifest file into a manifest with logging capabilities.
It does so by injecting the log analysis components into the input file.
"""

import argparse
import yaml
from elasticsearch import Elasticsearch
from yrca import yrca_process_logs
from utils import load_manifests, build_merged_text

DEFAULT_NAMESPACE = "log-enabled"



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
        help='Specify an output file pathname. If not specified, the output will be printed to stdout.',
    )
    parser.add_argument(
        "-t",
        "--timeout",
        default="15s",
        help="Specify a custom Envoy timeout. Defaults to 15s",
    )
    parser.add_argument(
        "-n",
        "--namespace",
        default="",
        help="Specify a suffix for the namespace (resulting in log-enabled-suffix)",
    )
    parser.add_argument(
        "--no-header", action="store_true", help="Do not add the Istio and ELK Stack components to the output file (useful for adding deployments to an already running main deployment file)"
    )
    parser.add_argument(
        "-c", "--connect", help="Connect to the specified Elasticsearch instance", type=str
    )
    parser.add_argument(
        "-p", "--port", default=9200, help="Elasticsearch port", type=int
    )
    parser.add_argument(
        "--pod", help="Dumps the logs of the specified pod (to a file, if used with -o). Cannot be used with yRCA log output format.", type=str
    )
    parser.add_argument(
        "--dump-all", action="store_true",  help="Dump all the logs in the Elasticsearch instance (to a file, if used with -o). Cannot be used with yRCA log output format.")
    parser.add_argument(
        "-f", "--format", choices=['yrca', 'gelf', 'syslog'], default='yrca', help="Specify the format of the logs to be processed. Defaults to yrca."
        )
    return parser.parse_args()

def inject(yaml_file, timeout="1m", no_header=False, custom_namespace_suffix=""):
    """
    Inject log analysis components into a YAML file.
    """
    final_namespace = DEFAULT_NAMESPACE
    if custom_namespace_suffix:
        final_namespace = DEFAULT_NAMESPACE + "-" + custom_namespace_suffix
        
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
        
        namespace_template = yaml.safe_load(manifests["manifest/namespace_manifest.yaml"])
        namespace_template["metadata"]["name"] = final_namespace
        docs_text.append(yaml.dump(namespace_template, default_flow_style=False))
                


        for doc in yaml.safe_load_all(manifests[yaml_file]):
            if doc:
                doc = replace_namespace(doc, final_namespace)
                if doc["kind"].lower() == "service":
                    service_name = doc["metadata"]["name"]
                    virtual_service = create_virtual_service(service_name, timeout, final_namespace)
                    virtual_services.append(virtual_service)
                docs_text.append(yaml.dump(doc, default_flow_style=False))

        
        virtual_services_text = [
            yaml.dump(vs, default_flow_style=False) for vs in virtual_services
        ]
        if no_header:
            merged_text = build_merged_text(docs_text + virtual_services_text)

        else:
            merged_text = build_merged_text(
                [
                    manifests["manifest/istio_manifest.yaml"],
                    manifests["manifest/elk_manifest.yaml"],
                ]
                + docs_text
                + virtual_services_text
            )
    except FileNotFoundError as exc:
        print(exc)

    return merged_text


def replace_namespace(yaml_section, namespace):
    """
    Replace or set the namespace in the YAML section.
    """
    if "metadata" not in yaml_section:
        yaml_section["metadata"] = {}
    yaml_section["metadata"]["namespace"] = namespace
    return yaml_section


def create_virtual_service(service_name, timeout, namespace):
    """
    Create an Istio VirtualService configuration for a given service.
    """
    return {
        "apiVersion": "networking.istio.io/v1alpha3",
        "kind": "VirtualService",
        "metadata": {"name": service_name, "namespace": namespace},
        "spec": {
            "hosts": [service_name],
            "http": [
                {"route": [{"destination": {"host": service_name}}], "timeout": timeout}
            ],
        },
    }


def connect_elasticsearch(es_host="localhost", port=9200, dump_all=False, format="yrca", pod=None, custom_namespace_suffix=""):

    if format == "yrca" and (dump_all or pod):
        print("The yRCA format (the default) only requires the dump of Envoy proxies, so it cannot be used with --dump-all or --pod. Specify a custom format with -f.")
        return None
    
    if dump_all and pod:
        print("Cannot use --dump-all and --pod together.")
        return None
    
    final_namespace = DEFAULT_NAMESPACE
    if custom_namespace_suffix:
        final_namespace = DEFAULT_NAMESPACE + "-" + custom_namespace_suffix

    # Connect to the Elasticsearch instance
    es = Elasticsearch([{"host": es_host, "port": port, "scheme": "http"}])

    # Define the query
    query = {
        "bool": {
            "must": [
                {"match": {"kubernetes.namespace": final_namespace}},
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
    elif pod:
        query = {
            "bool": {
                "must": [
                    {"match": {"kubernetes.namespace": "log-enabled"}},
                    {"match": {"kubernetes.pod.name.keyword": pod}},
                ],
                "must_not": [
                {"match": {"kubernetes.container.name": "istio-proxy"}}
            ]
            }
        }

    # Use the scroll API
    scroll_time = "1m"
    size = 10000

    try:
        response = es.search(index="logstash-*", query=query, scroll=scroll_time, size=size, sort="@timestamp:asc")
    except Exception as e:
        print("Error while connecting to Elasticsearch instance. The error is specified below.")
        print(e)
        return None

    logs = []

    # While there are logs to fetch, keep fetching
    while len(response['hits']['hits']):
        for hit in response["hits"]["hits"]:
            if format == "yrca":
                pod_name = hit["_source"]["kubernetes"]["pod"]["name"]
                log_message = hit["_source"]["message"]
                formatted_log = f"{pod_name} {log_message}"
                logs.append(formatted_log)

            elif format == "gelf":
                version = "1.1"
                host = hit["_source"]["host"]["name"]
                short_message = hit["_source"]["message"].split("\n")[0]
                full_message = hit["_source"]["message"]
                timestamp = hit["_source"]["@timestamp"]
                namespace_name = hit["_source"]["kubernetes"]["namespace"]
                pod_name = hit["_source"]["kubernetes"]["pod"]["name"]
                container_name = hit["_source"]["kubernetes"]["container"]["name"]
                level = "INFO"
                formatted_log = f'{{"version": "{version}", "host": "{host}", "short_message": "{short_message}", "full_message": "{full_message}", "timestamp": "{timestamp}", "level": "{level}", "_namespace_name": "{namespace_name}", "_pod_name": "{pod_name}", "_container_name": "{container_name}"}}'
                logs.append(formatted_log)

            elif format == "syslog":
                priority = "<134>"
                timestamp = hit["_source"]["@timestamp"]
                hostname = hit["_source"]["host"]["name"]
                app_name = hit["_source"]["kubernetes"]["container"]["name"]
                procid = hit["_source"]["kubernetes"]["pod"]["name"]
                msg = hit["_source"]["message"]
                formatted_log = f"{priority}{timestamp} {hostname} {app_name} {procid} {msg}"
                logs.append(formatted_log)

        # Fetch the next batch of logs using the scroll API
        response = es.scroll(scroll_id=response['_scroll_id'], scroll=scroll_time)
    
    es.clear_scroll(scroll_id=response['_scroll_id'])

    # Post-process logs for yrca
    if format == "yrca":
        logs = yrca_process_logs(logs)

    return logs

def main():
    """
    Main function to execute the script.
    """
    args = parse_options()
    if args.inject:
        output = inject(args.inject, args.timeout, args.no_header, args.namespace)
    if args.connect:
        output = connect_elasticsearch(args.connect, args.port, args.dump_all, args.format, args.pod, args.namespace)

    if not output:
        return
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            if isinstance(output, list):
                stream.write("\n".join(output))
            else:
                stream.write(output)
            print(f"Output file written to {args.output}")
    else:
        if isinstance(output, list):
            print("\n".join(output))
        else:
            print(output)
   




if __name__ == "__main__":
    main()
