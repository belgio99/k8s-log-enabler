import json
from datetime import datetime, timedelta

logs = []

def produce_yrca_logs(requestJson, responseJson):
    """Process and print logs based on request and response data."""

    responseCode = requestJson.get("response_code", None)
    requestID = requestJson.get("x-request-id", "")
    requestServiceName = "k8s_" + requestJson.get("pod_name", "").split("-")[0]
    requestStartTime = requestJson.get("start_time", "")

    if responseJson:
        responseServiceName = "k8s_" + responseJson["pod_name"].split("-")[0]
        responseStartTime = responseJson["start_time"]
    else:
        responseServiceName = requestJson.get("authority", "")

    # Define common print pattern
    def append_log(time, message_pattern, severity, *args, ):
        timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        formatted_time = datetime.strptime(time, timestamp_format).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        event_msg = message_pattern.format(*args)
        
        log_entry = {
            "severity": severity,
            "container_name": requestServiceName,
            "event": event_msg,
            "message": f"{formatted_time} {severity} {requestServiceName} --- {event_msg}",
            "timestamp": formatted_time,
            "@timestamp": time
        }
        logs.append(log_entry)

    if not responseJson:
        append_log(requestStartTime, "Sending message to {} (request_id: [{}])", "INFO",responseServiceName, requestID)
        
        requestDateTime = datetime.strptime(requestStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta = timedelta(milliseconds=requestJson["duration"])
        requestEndTime = (requestDateTime + delta).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        
        exception_reason = ""
        append_log(requestEndTime, "Failing to contact {} (request_id: [{}]). Root cause: {}", "ERROR",requestJson["authority"], requestID, exception_reason)
    else:
        append_log(requestStartTime, "Sending message to {} (request_id: [{}])", "INFO",responseServiceName, requestID)
        
        append_log(responseStartTime, "Received POST request from {} (request_id: {})", "INFO",requestJson["authority"], requestID)
        
        responseDateTime = datetime.strptime(responseStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta1 = timedelta(milliseconds=responseJson["duration"])
        responseEndTime = (responseDateTime + delta1).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        
        if responseCode == 200:
            append_log(responseEndTime, "Answered to POST request from {} with code: {} (request_id: {})", "INFO",requestJson["authority"], responseCode, requestID)
        else:
            append_log(responseEndTime, "Answered to POST request from {} with code: {} (request_id: {})", "ERROR",requestJson["authority"], responseCode, requestID)
        
        requestDateTime = datetime.strptime(requestStartTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta2 = timedelta(milliseconds=requestJson["duration"])
        requestEndTime = (requestDateTime + delta2).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + "Z"
        
        if responseCode == 200:
            append_log(requestEndTime, "Receiving answer from {} (request_id: [{}])", "INFO",responseServiceName, requestID)
        else:
            append_log(requestEndTime, "Error response (code: {}) received from {} (request_id: [{}])", "ERROR", responseCode, responseServiceName, requestID)


def yrca_process_logs(log_lines):
    """Process the provided list of log lines."""

    ToBeProcessed = {}

    for line in log_lines:
        podName, log = line.split(' ', 1)
        podName = podName.split("_")[0]
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
