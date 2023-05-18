import argparse

from utils import *
from istio import *
from kubernetes import *



def parseArgs():

    parser = argparse.ArgumentParser(description="Progetto Tesi")
    parser.add_argument("--istio-profile", help="Name of the Istio profile to use. See https://istio.io/latest/docs/setup/additional-setup/config-profiles/ for more information. You cannot use this option and --istio-file at the same time.")
    parser.add_argument("--istio-file", help="If you already have a custom Istio file, you can specify it here. You cannot use this option and --istio-profile at the same time.")
    parser.add_argument("--k8s-namespace",  default="default", help="The Kubernetes namespace to use. If not specified, the default namespace will be used.")
    parser.add_argument("--auto-sc-inject", action="store_true", help="Enable automatic sidecar injection for the specified namespace. If not specified, automatic sidecar injection will be disabled for the specified namespace.")
    #parser.add_argument("--dry-run", action="store_true", help="Dry run the YAML file without applying it")
    return parser.parse_args()



def main():
    args = parseArgs()
    checkInstallation()
    installIstioConfig(args.istio_profile, args.istio_file)
    if args.auto_sc_inject:
        enableSidecarInjection(args.k8s_namespace)

    


if(__name__ == "__main__"):
    main()

