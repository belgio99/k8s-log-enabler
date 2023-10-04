"""
Standalone module for yRCA-compatible log processing.
"""

import json
from datetime import datetime, timedelta

logs = []


def produce_yrca_logs(request_json, response_json):
    """Process and print logs based on request and response data."""

    response_code = request_json.get("response_code", None)
    request_id = request_json.get("x-request-id", "")
    request_service_name = "".join(
        request_json.get("pod_name", "").rsplit("-", 2)[0].split("-")
    )
    request_start_time = request_json.get("start_time", "")
    response_flags = request_json.get("response_flags", "")

    if not request_id:
        return

    if response_json:
        response_service_name = "".join(
            response_json.get("pod_name", "").rsplit("-", 2)[0].split("-")
        )
        response_start_time = response_json["start_time"]
    else:
        response_service_name = request_json.get("authority", "").split(":")[0]

    def append_log(time, message_pattern, severity, *args):
        timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        formatted_time = datetime.strptime(time, timestamp_format).strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]
        event_msg = message_pattern.format(*args)
        log_entry = {
            "severity": severity,
            "container_name": "k8s_" + request_service_name,
            "event": event_msg,
            "message": f"{formatted_time} {severity} {request_service_name} --- {event_msg}",
            "timestamp": formatted_time,
            "@timestamp": time,
        }
        logs.append(json.dumps(log_entry))

    if request_service_name == response_service_name:
        return
    append_log(
        request_start_time,
        "Sending message to {} (request_id: [{}])",
        "INFO",
        response_service_name,
        request_id,
    )

    if not response_json or response_code not in [200, None]:
        request_date_time = datetime.strptime(request_start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        delta = timedelta(milliseconds=request_json["duration"])
        request_end_time = (request_date_time + delta).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[
            :-4
        ] + "Z"
        if response_code == 0 or response_flags == "UH":
            append_log(
                request_end_time,
                "Failing to contact {} (request_id: [{}]). Root cause: ",
                "ERROR",
                request_json["authority"].split(":")[0],
                request_id,
            )
        elif response_code != 200:
            append_log(
                request_end_time,
                "Error response (code: {}) received from {} (request_id: [{}])",
                "ERROR",
                response_code,
                response_service_name,
                request_id,
            )
    if response_json:
        buf = response_service_name
        response_service_name = request_service_name
        request_service_name = buf
        append_log(
            response_start_time,
            "Received POST request from {} (request_id: {})",
            "INFO",
            response_service_name,
            request_id,
        )
        response_date_time = datetime.strptime(response_start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        delta = timedelta(milliseconds=response_json["duration"])
        response_end_time = (response_date_time + delta).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[
            :-4
        ] + "Z"
        append_log(
            response_end_time,
            "Answered to POST request from {} with code: {} (request_id: {})",
            "INFO",
            response_service_name,
            response_code,
            request_id,
        )


def yrca_process_logs(log_lines):
    """Process the provided list of log lines."""

    to_be_processed = {}

    for line in log_lines:
        pod_name, log = line.split(" ", 1)
        pod_name = pod_name.split("_")[0]
        if log[-1] == "}":
            json_log = json.loads(log)
            json_log["pod_name"] = pod_name
            request_id = json_log["x-request-id"]
            authority = json_log["authority"]

            conditions = [
                json_log.get("response_code") == 408,
                json_log.get("response_code") == 504
                and json_log.get("response_flags") == "UT"
                and json_log.get("response_code_details") == "response_timeout",
                json_log.get("response_code") == 503
                and (json_log.get("duration") and json_log.get("duration") > 0)
                and all(
                    not json_log.get(key) or json_log.get(key) <= 0
                    for key in [
                        "request_tx_duration",
                        "response_duration",
                        "response_tx_duration",
                    ]
                ),
                json_log.get("response_flags") == "UH",
            ]

            if any(conditions):
                produce_yrca_logs(json_log, None)
                continue

            key = (request_id, authority)
            if key in to_be_processed and to_be_processed[key]["pod_name"] != pod_name:
                old_json_log = to_be_processed.pop(key)
                timestamp1 = json_log["start_time"]
                timestamp2 = old_json_log["start_time"]
                date1 = datetime.strptime(timestamp1, "%Y-%m-%dT%H:%M:%S.%fZ")
                date2 = datetime.strptime(timestamp2, "%Y-%m-%dT%H:%M:%S.%fZ")
                if date1 < date2:
                    produce_yrca_logs(json_log, old_json_log)
                else:
                    produce_yrca_logs(old_json_log, json_log)
            else:
                to_be_processed[key] = json_log

    return logs


__all__ = ["yrca_process_logs"]
