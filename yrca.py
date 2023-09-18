import json
from datetime import datetime, timedelta

logs = []

def produce_yrca_logs(requestJson, responseJson):
    """Process and print logs based on request and response data."""

    responseCode = requestJson.get("response_code", None)
    severity = get_severity(responseCode) if responseCode else "INFO"
    requestID = requestJson.get("x-request-id", "")
    requestServiceName = requestJson.get("pod_name", "")
    requestStartTime = requestJson.get("start_time", "")

    if responseJson:
        responseServiceName = responseJson["pod_name"]
        responseStartTime = responseJson["start_time"]
    else:
        responseServiceName = requestJson.get("authority", "")

    # Define common print pattern
    def append_log(time, service_name, action, target_service, severity, req_id):
        event_msg = f"{action} {target_service} (request_id: {req_id})"
        timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        formatted_time = datetime.strptime(time, timestamp_format).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        log_entry = {
            "severity": severity,
            "container_name": service_name,
            "event": event_msg,
            "message": f"{formatted_time} {severity} {service_name} --- {event_msg}",
            "timestamp": formatted_time,
            "@timestamp": time
        }
        logs.append(log_entry)


    if not responseJson:
        append_log(requestStartTime, requestServiceName, "Sending message to", responseServiceName, severity, requestID)
        requestDateTime = datetime.strptime(requestStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta = timedelta(milliseconds=requestJson["duration"])
        requestEndTime = (requestDateTime + delta).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        append_log(requestEndTime, requestServiceName, "Failing to contact", requestJson["authority"], severity, requestID)

    else:
        append_log(requestStartTime, requestServiceName, "Sending message to", responseServiceName, severity, requestID)
        append_log(responseStartTime, responseServiceName, "Received POST request from", requestServiceName, severity, requestID)
        responseDateTime = datetime.strptime(responseStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta1 = timedelta(milliseconds=responseJson["duration"])
        responseEndTime = (responseDateTime + delta1).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        append_log(responseEndTime, responseServiceName, "Answered to POST request from", requestServiceName, severity, requestID)
        requestDateTime = datetime.strptime(requestStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta2 = timedelta(milliseconds=requestJson["duration"])
        requestEndTime = (requestDateTime + delta2).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        status_msg = "Received response OK from" if responseCode == 200 else "Error response "
        append_log(requestEndTime, requestServiceName, status_msg, responseServiceName, severity, requestID)

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

def get_severity(response_code):
    """Deduce severity based on the response code."""
    if response_code >= 500:
        return "ERROR"
    elif response_code >= 400:
        return "WARN"
    else:
        return "INFO"


__all__ = ['yrca_process_logs']
