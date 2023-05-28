import os, sys, yaml, subprocess

ACCESS_LOG_FILE = "/dev/stdout"
ACCESS_LOG_ENCODING = "JSON"
ORIG_ISTIO_FILENAME = "input/istioConfig" # the YAML file containing the original Istio configuration
NEW_ISTIO_FILENAME = "output/newistioConfig" # the YAML file containing the edited Istio configuration (with access logs)




def installIstioConfig(istioConfigProfile, istioConfigFile):
    # check if the user wrongly specified both a profile and a file
    if istioConfigProfile != None and istioConfigFile != None:
        print("Error: You cannot use --istio-profile and --istio-file at the same time")
        sys.exit(1)

    if istioConfigFile != None:
        print("Using Istio YAML file: " + istioConfigFile)

        try:
            istioConfigFile = open(istioConfigFile, "r")
        except FileNotFoundError:
            print("Error: The Istio YAML file does not exist")
            sys.exit(1)


        config = yaml.safe_load(istioConfigFile)

        dataKeys = list(config.keys())
        if "spec" in dataKeys:
                if "meshConfig" in list(config.get("spec")):
                    config = configureAccessLogs(config)
                else:
                    config["spec"]["meshConfig"] = {}
                    config = configureAccessLogs(config)
        else:
            print("Error: The Istio YAML file is not valid")
            sys.exit(1)

        # write the new YAML file
        newIstioConfigFile = open(NEW_ISTIO_FILENAME + ".yaml", "w")
        yaml.dump(config, newIstioConfigFile)
        newIstioConfigFile.close()

        cmd = "istioctl install -f " + NEW_ISTIO_FILENAME + ".yaml"
        subprocess.run(cmd, shell=True)

    
    elif istioConfigProfile == None:
        # get the YAML for the default profile
        print("No Istio profile specified:")
        istioConfigProfile = "default"



    # get the YAML for the specified profile
    print("Using Istio profile: " + istioConfigProfile + "\n")
    if os.system(
        "istioctl profile dump " + istioConfigProfile + " > " + ORIG_ISTIO_FILENAME + ".yaml"
    ) != 0:
        print("Error in retrieving the Istio profile configuration")
        sys.exit(1)
    istioConfigFile = open(ORIG_ISTIO_FILENAME + ".yaml", "r")
    config = yaml.safe_load(istioConfigFile)
    config = configureAccessLogs(config)
    
    newIstioConfigFile = open(NEW_ISTIO_FILENAME + ".yaml", "w")
    yaml.dump(config, newIstioConfigFile)
    newIstioConfigFile.close()

    cmd = "istioctl install -f " + NEW_ISTIO_FILENAME + ".yaml"
    subprocess.run(cmd, shell=True)

    return

def configureAccessLogs(config):
    config["spec"]["meshConfig"]["accessLogFile"] = ACCESS_LOG_FILE
    config["spec"]["meshConfig"]["accessLogEncoding"] = ACCESS_LOG_ENCODING
    config["spec"]["meshConfig"][
        "accessLogFormat"
    ] = '{\n  "start_time": "%START_TIME%",\n  "method": "%REQ(:METHOD)%",\n  "protocol": "%PROTOCOL%",\n  "response_code": "%RESPONSE_CODE%",\n  "response_code_details": "%RESPONSE_CODE_DETAILS%",\n  "connection_termination_details": "%CONNECTION_TERMINATION_DETAILS%",\n  "upstream_request_attempt_count": "%UPSTREAM_REQUEST_ATTEMPT_COUNT%",\n  "duration": "%DURATION%",\n  "request_duration": "%REQUEST_DURATION%",\n  "request_tx_duration": "%REQUEST_TX_DURATION%",\n  "response_duration": "%RESPONSE_DURATION%",\n  "response_tx_duration": "%RESPONSE_TX_DURATION%",\n  "response_flags": "%RESPONSE_FLAGS%",\n  "route_name": "%ROUTE_NAME%",\n  "authority": "%REQ(:AUTHORITY)%",\n  "connection_id": "%CONNECTION_ID%",\n  "x-request-id": "%REQ(X-REQUEST-ID)%",\n  "x-envoy-upstream-service-time": "%RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%"\n}'
    return config


