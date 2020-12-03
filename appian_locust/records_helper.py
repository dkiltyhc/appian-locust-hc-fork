from .helper import extract_values, find_component_by_attribute_in_dict, log_locust_error
from typing import Dict, Any, Tuple


def get_all_records_from_json(json_response: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    is_grid = _is_grid(json_response)
    records = {}
    error_key_string = "ERROR::"
    error_key_count = 0
    if is_grid:
        all_record_items = extract_values(json_response, "#t", "RecordLink")
        # extract all RecordLinks out of the response directly
        for record_item in all_record_items:
            try:
                opaque_id = record_item["_recordRef"]
                label = record_item["label"]
                key = label + "::" + opaque_id
                records[key] = record_item
            except Exception as e:
                error_key_count += 1
                records[error_key_string + str(error_key_count)] = {}
                log_locust_error(e, error_desc="Corrupt Record Error")
    else:
        all_linked_items = extract_values(json_response, "#t", "LinkedItem")
        for current_item in all_linked_items:
            record_link_raw = extract_values(current_item, "#t", "RecordLink")
            if len(record_link_raw) > 0:
                label_raw = extract_values(current_item["values"], "#t", "string")
                record_item = record_link_raw[0]
                try:
                    opaque_id = record_item["_recordRef"]
                    label = label_raw[0]["#v"]
                    record_item["label"] = label
                    key = label + "::" + opaque_id
                    records[key] = record_item
                except Exception as e:
                    error_key_count += 1
                    records[error_key_string + str(error_key_count)] = {}
                    log_locust_error(e, error_desc="Corrupt Record Error", raise_error=False)
    return records, error_key_count


def get_record_summary_view_response(form_json: Dict[str, Any]) -> str:
    """
        This returns the contents of "x-embedded-summary" from Record Instance's Feed response
    """
    # SAIL Code for the Record Summary View is embedded within the response.
    record_summary_response = find_component_by_attribute_in_dict("name", "x-embedded-summary", form_json).get("children")
    if not record_summary_response or len(record_summary_response) < 1:
        log_locust_error(Exception("Parser was not able to find embedded SAIL code within JSON response for the requested Record Instance."),
                         location="records_helper.py/get_record_summary_view_response()",
                         raise_error=True
                         )
    return record_summary_response[0]


def get_record_header_response(form_json: Dict[str, Any]) -> str:
    """
        This returns the contents of "x-embedded-header" from Record Instance's Feed response.
        Header response is needed in cases like clicking on a related action.
    """
    # SAIL Code for the Record Header is embedded within the response.
    record_header_response = find_component_by_attribute_in_dict("name", "x-embedded-header", form_json).get("children")
    if not record_header_response or len(record_header_response) < 1:
        log_locust_error(Exception("Parser was not able to find embedded SAIL code within JSON response for the requested Record Instance."),
                         location="records_helper.py/get_record_header_response()",
                         raise_error=True
                         )
    return record_header_response[0]


def _is_grid(res_dict_var: Dict[str, Any]) -> bool:
    return any([len(extract_values(res_dict_var, "testLabel", "recordGrid")) != 0,
                len(extract_values(res_dict_var, "testLabel", "recordGridInstances")) != 0])
