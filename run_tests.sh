#!/bin/bash

ISTIO_NAMESPACE="log-istio-system"
ELK_NAMESPACE="log-elk"
TMP_FILE="minikube_service_output.txt"

function show_help() {
    echo "Usage: $0 <DEPLOYMENT_FILE> <NAMESPACE> <SERVICE_NAME> <DEPLOYMENT_NAME> <DEPLOY_SLEEP_TIME> <CLEANUP_SLEEP_TIME> <SERVICE_SUBLINK>"
    echo "Automates performance testing for Kubernetes deployments."
    echo "Check the script comments or README for more details."
}

function get_service_url() {
    local SERVICE_NAME=$1
    local NAMESPACE=$2

    minikube service $SERVICE_NAME --url -n $NAMESPACE > $TMP_FILE &
    sleep 10
    SERVICE_URL=$(sed -n '2p' $TMP_FILE)
    rm -f $TMP_FILE

    echo $SERVICE_URL
}

function run_tests() {
    local DEPLOY_FILE=$1
    local NAMESPACE=$2
    local SERVICE_NAME=$3
    local DEPLOYMENT_NAME=$4
    local DEPLOY_SLEEP=$5
    local CLEANUP_SLEEP=$6
    local SERVICE_SUBLINK=$7
    local OUTPUT_FILE="${DEPLOYMENT_NAME}_metrics.csv"

    echo "Applying deployment from $DEPLOY_FILE..."
    kubectl apply -f $DEPLOY_FILE

    echo "Waiting for $DEPLOY_SLEEP seconds to let the deployment stabilize..."
    sleep $DEPLOY_SLEEP

    SERVICE_URL=$(get_service_url $SERVICE_NAME $NAMESPACE)
    SERVICE_URL="${SERVICE_URL}${SERVICE_SUBLINK}"

    # Run the test for different user loads
    for USERS in 1; do
        echo "Running tests simulating $USERS users..." >> $OUTPUT_FILE
        wrk -t 1 -c$USERS -d60s $SERVICE_URL --latency >> $OUTPUT_FILE
    done

    echo "Writing performance metrics to $OUTPUT_FILE..."

    echo "Cleanup: Removing the applied deployment..."
    kubectl delete -f $DEPLOY_FILE

    echo "Waiting for $CLEANUP_SLEEP seconds to ensure complete cleanup..."
    sleep $CLEANUP_SLEEP
}

# Verify correct usage
if [ "$1" == "--help" ] || [ "$1" == "-h" ] || [ "$#" -ne 7 ]; then
    show_help
    exit 1
fi

# Start the main script
echo "Starting performance testing..."
run_tests $1 $2 $3 $4 $5 $6 $7
echo "Performance testing completed!"
