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

        # Get strategy templates
        templates = client.get_scheduling_unit_observing_strategy_templates()

        # Print template information
        for template in templates:
            print(f"{template['id']:4d} | {template['name']} | v{template['version']} | {template['state_value']}")
            
