#!/usr/bin/env python3
import json

from tmss_http_rest_client import TMSSsession

if __name__ == "__main__":
    # Read credentials
    with open("login.json", "r") as fp:
        login = json.load(fp)

    # Open session
    with TMSSsession(host=login["host"],
                     port=login["port"],
                     username=login["username"],
                     password=login["password"]) as client:

        # Get SU draft
        url = "https://host.at.url/api/scheduling_unit_draft/XXXX"
        spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=url)

        print(spec_doc)

