#!/usr/bin/env python3
import os
import sys
import yaml
import argparse

import astropy.units as u
from astropy.coordinates import SkyCoord

from tmss_http_rest_client import TMSSsession

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Schedule pulsar timing observations in TMSS")
    parser.add_argument("-r", "--run", help="YAML specification of observing run",
                        metavar="FILE")
    parser.add_argument("-u", "--upload", help="Create specification documents and upload to TMSS",
                        action="store_true")
    parser.add_argument("sources", help="Input source files [YAML]", nargs="*", metavar="FILE")
    args = parser.parse_args()

    # Input argument logic
    if args.sources == []:
        print("No source files provided.")
        sys.exit()
    
    # Read credentials
    with open("login.yaml", "r") as fp:
        settings = yaml.full_load(fp)
        
    # Read observation run settings
    with open(args.run, "r") as fp:
        run_spec = yaml.full_load(fp)
    print(f"Read observing run specification from {args.run}")

    # Read sources
    sources = []
    for filename in args.sources:
        with open(filename, "r") as fp:
            source = yaml.full_load(fp)
            print(f"Read source specification from {filename} for {source['name']}")
            sources.append(source)
    print(f"Read {len(sources)} source specifications")
        
    # Open session
    with TMSSsession(host=settings['host'],
                     port=settings['port'],
                     username=settings['username'],
                     password=settings['password']) as client:
        print("Opened TMSS connection")
        
        # Get the latest satellite monitoring template
        template = client.get_scheduling_unit_observing_strategy_template(run_spec['strategy_name'])
        print(f"Using strategy template {template['url']}")
        
        # Get the specifications document
        original_spec_doc = client.get_scheduling_unit_observing_strategy_template_specification_with_just_the_parameters(template['name'], template['version'])

        # Loop over sources
        for src_spec in sources:
            # Pointing dict
            name = src_spec['name']
            p = SkyCoord(ra=src_spec['angle1'], dec=src_spec['angle2'], unit=("hourangle", "deg"), frame="icrs")
            pointing = {'angle1': p.ra.rad,
                        'angle2': p.dec.rad,
                        'direction_type': 'J2000',
                        'target': name}

            # Station setup
            station_groups = [{'max_nr_missing': run_spec['max_nr_missing'],
                               'stations': run_spec['stations']}]

            # Copy original specification document
            spec_doc = original_spec_doc.copy()

            # Adjust specifications
            spec_doc['tasks']['Observation']['short_description'] = name
            spec_doc['tasks']['Observation']['specifications_doc']['duration'] = src_spec['duration_s']
            spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['SAPs'] = [{'digital_pointing': pointing}]
            spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['tile_beam'] = pointing
            spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['station_groups'] = station_groups
            spec_doc['tasks']['Pipeline']['short_description'] = f"{name}/PULP"
            spec_doc['scheduling_constraints_doc']['sky']['min_elevation']['target'] = src_spec['elev_min_deg'] * u.deg.to(u.rad)
            spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['from'] = src_spec['lst_min_s']
            spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['to'] = src_spec['lst_max_s']
            if 'timebefore' in run_spec and 'timebetween' in run_spec:
                print("Error: Can not have timebefore and timebetween constraints")
                continue
            elif 'timebefore' in run_spec:
                spec_doc['scheduling_constraints_doc']['time']['before'] = run_spec['timebefore']
            elif 'timebetween' in run_spec:
                spec_doc['scheduling_constraints_doc']['time']['between'] = run_spec['timebetween']

            # Show spec doc
            print(spec_doc)
            print()

            # Validate spec doc
#            result = client.validate_template_specifications_doc(template['url'], spec_doc)
#            print(result)
            
            # Skip if dryrun
            if not args.upload:
                print("No scheduling units uploaded to TMSS.")
                print()
                continue

            # Create scheduling unit
            scheduling_unit_draft = client.create_scheduling_unit_draft_from_strategy_template(template['id'], run_spec['scheduling_set_id'], spec_doc, name, priority_queue=src_spec['priority_queue'])

            # Patch scheduling unit with keys that are not included in the strategy
            url = scheduling_unit_draft['url']
            json_data = {"rank": src_spec['rank'],
                         "description": run_spec['description']}
            response = client.do_request_and_get_result_as_json_object(method="PATCH", full_url=url, json_data=json_data)
            print(f"Created SU {scheduling_unit_draft['id']} for {name} at {scheduling_unit_draft['url']}")
