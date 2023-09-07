import json
from datetime import datetime, timedelta

logs = []

def produce_yrca_logs(requestJson, responseJson):
    """Process and print logs based on request and response data."""
    
    responseCode = requestJson.get("response_code", None)
    requestID = requestJson.get("x-request-id", "")
    requestServiceName = requestJson.get("pod_name", "")
    requestStartTime = requestJson.get("start_time", "")

    if responseJson:
        responseServiceName = responseJson["pod_name"]
        responseStartTime = responseJson["start_time"]
    else:
        responseServiceName = requestJson.get("authority", "")

    # Define common print pattern
    def append_log(time, service_name, action, target_service, req_id):
        logs.append(f"{time} - INFO - {service_name} - {action} {target_service} (request_id: {req_id})")

    if not responseJson:
        append_log(requestStartTime, requestServiceName, "Sending request to", responseServiceName, requestID)
        requestDateTime = datetime.strptime(requestStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta = timedelta(milliseconds=requestJson["duration"])
        requestEndTime = (requestDateTime + delta).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        append_log(requestEndTime, requestServiceName, "Failing to contact", requestJson["authority"], requestID)

    else:
        append_log(requestStartTime, requestServiceName, "Sending request to", responseServiceName, requestID)
        append_log(responseStartTime, responseServiceName, "Reading request from", requestServiceName, requestID)
        responseDateTime = datetime.strptime(responseStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta1 = timedelta(milliseconds=responseJson["duration"])
        responseEndTime = (responseDateTime + delta1).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        append_log(responseEndTime, responseServiceName, "Answering response to", requestServiceName, requestID)
        requestDateTime = datetime.strptime(requestStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta2 = timedelta(milliseconds=requestJson["duration"])
        requestEndTime = (requestDateTime + delta2).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        status_msg = "Received response OK from" if responseCode == 200 else "Received response ERROR from"
        append_log(requestEndTime, requestServiceName, status_msg, responseServiceName, requestID)

def yrca_process_logs(log_lines):
    """Process the provided list of log lines."""
    
    ToBeProcessed = {}

    for line in log_lines:
        podName, log = line.split(' ', 1)
        if log[-1] == "}":
            jsonLog = json.loads(log)
            jsonLog["pod_name"] = podName
            requestID = jsonLog["x-request-id"]
            authority = jsonLog["authority"]

            conditions = [
                jsonLog.get("response_code") == 408,
                jsonLog.get("response_code") == 504 and jsonLog.get("response_flags") == "UT" and jsonLog.get("response_code_details") == "response_timeout",
                jsonLog.get("response_code") == 503 and (jsonLog.get("duration") and jsonLog.get("duration") > 0) and all(not jsonLog.get(key) or jsonLog.get(key) <= 0 for key in ["request_tx_duration", "response_duration", "response_tx_duration"])
            ]


            if any(conditions):
                produce_yrca_logs(jsonLog, None)
                continue

            key = (requestID, authority)
            if key in ToBeProcessed and ToBeProcessed[key]["pod_name"] != podName:
                oldJsonLog = ToBeProcessed.pop(key)
                timestamp1 = jsonLog["start_time"]
                timestamp2 = oldJsonLog["start_time"]
                date1 = datetime.strptime(timestamp1, '%Y-%m-%dT%H:%M:%S.%fZ')
                date2 = datetime.strptime(timestamp2, '%Y-%m-%dT%H:%M:%S.%fZ')
                if date1 < date2:
                    produce_yrca_logs(jsonLog, oldJsonLog)
                else:
                    produce_yrca_logs(oldJsonLog, jsonLog)
            else:
                ToBeProcessed[key] = jsonLog

    return logs

__all__ = ['yrca_process_logs']
