#!/usr/bin/env python3

"""NOTE: This is a work in progress. Don't take any of these numbers as 100% accurate. More time needs to be 
   invested to ensure these figures are as accurate as possible.

   Usage: Use this script to compare the crawled models to the botocore SDK. This script will count the number of 
   undocumented services by different measuring criteria (more on what that means below).
   
   You should run this from the root directory of the project, I.E:
   
   ./scripts/compare-2-botocore.py <path to botocore>

   Compare by uid: This method uses the `uid` of a model as the primary key to compare between the botocore library 
   and the crawled models. Personally, I think this makes the most sense because the uid is a unique identifier for 
   a service and is a combination of the service name and version. However it does have a problem. There are a number
   of services that have the same name but different versions. For example, in the botocore library Athena only has 
   version 2017-05-18 (https://github.com/boto/botocore/blob/develop/botocore/data/athena/2017-05-18/service-2.json)
   but in the crawled models I have a 2016-04-27 version. Should this count as an undocumented service? I don't know?
   There are unique operations in the 2016-04-27 version that does not exist in the botocore 2017-05-18 version. 
   
   If we simply compare by `uid` we will get a large number of false positives since theoretically a large number of 
   operations that exist in the normal botocore models will considered "undocumented". In situations where that 
   service does not exist in botocore, this is not an issue.
   
   Compare by service name: To try and resolve the problems with comparing by `uid` we can also compare by service name. 
   Given a model such as `xray-2016-04-12.json` we extract out the service name (xray) and ignore the version. We then 
   deduplicate all operations across all versions of the service and compare them to the deduplicated versions in 
   botocore. This has the effect that if a service has multiple versions, we will only count the operations that are 
   unique."""


import os, json, sys

MODELS_DIR = "./models"

def main():
    check_botocore_dir()
    botocore_dir = f"{sys.argv[1]}/botocore/data"

    # Compare by UID
    compare_by_uid(MODELS_DIR, botocore_dir)
    compare_by_service_name(MODELS_DIR, botocore_dir)


def compare_by_service_name(model_dir, botocore_dir):
    # Slurp all botocore models into memory with `service_name` as the primary key
    botocore = {}
    for service in os.listdir(botocore_dir):
        if not os.path.isdir(f"{botocore_dir}/{service}"):
            continue

        for version in os.listdir(f"{botocore_dir}/{service}/"):
            if not os.path.isdir(f"{botocore_dir}/{service}/{version}"):
                continue

            if not os.path.exists(f"{botocore_dir}/{service}/{version}/service-2.json"):
                continue

            with open(f"{botocore_dir}/{service}/{version}/service-2.json", "r") as r:
                data = json.load(r)
                if 'uid' not in data['metadata'].keys():
                    continue

                # Split on -2 (This is to catch all the year 2000)
                service_name = data['metadata']['uid'].split("-2")[0]

                if service_name not in botocore.keys():
                    botocore[service_name] = []

                for operation in data['operations'].keys():
                    if operation not in botocore[service_name]:
                        botocore[service_name].append(operation)

    # Search through all crawled model definitions and compare to botocore
    # If something is not in botocore, alert
    # We print in the weird format to support markdown linking
    undocumented_services_count = 0
    undocumented_actions_count = 0

    modelfiles = os.listdir(model_dir)
    for file in modelfiles:
        if file[-5:] != ".json":
            continue

        with open(f"{model_dir}/{file}", "r") as r:
            data = json.load(r)
        
        # First check if the service name exists in botocore. If not, all operations are free game
        service_name = data['metadata']['uid'].split("-2")[0]
        if "-1" in service_name:
            service_name = data['metadata']['uid'].split("-1")[0]

        if service_name not in botocore.keys():
            #print(f"{data['metadata']['uid']} not found  ")
            undocumented_services_count += 1
            for operation in data['operations'].keys():
                internal = ""
                if "internalonly" in data['operations'][operation].keys():
                    internal = "internalonly"
                undocumented_actions_count += 1
                #print(f"[v]({MODELS_DIR}/{file}) - {data['metadata']['uid']}:{operation} {internal}  ")
        
        # else, if the serivce_names's match, compare the operations
        elif service_name in botocore.keys():
            for operation in data['operations']:
                if operation not in botocore[service_name]:
                    internal = ""
                    if "internalonly" in data['operations'][operation].keys():
                        internal = "internalonly"
                    undocumented_actions_count += 1
                    #print(f"[v]({MODELS_DIR}/{file}) - {data['metadata']['uid']}:{operation} {internal}  ")

    print(f"Total undocumented services by service name: {undocumented_services_count}")
    print(f"Total undocumented actions by service name: {undocumented_actions_count}")


def compare_by_uid(model_dir, botocore_dir):
    # Slurp all botocore models into memory with `uid` as the primary key
    botocore = {}
    for service in os.listdir(botocore_dir):
        if not os.path.isdir(f"{botocore_dir}/{service}"):
            continue

        for version in os.listdir(f"{botocore_dir}/{service}/"):
            if not os.path.isdir(f"{botocore_dir}/{service}/{version}"):
                continue

            if not os.path.exists(f"{botocore_dir}/{service}/{version}/service-2.json"):
                continue

            with open(f"{botocore_dir}/{service}/{version}/service-2.json", "r") as r:
                data = json.load(r)
                if 'uid' not in data['metadata'].keys():
                    continue
                botocore[data['metadata']['uid']] = data

    # Search through all crawled model definitions and compare to botocore
    # If something is not in botocore, alert
    # We print in the weird format to support markdown linking
    undocumented_services_count = 0
    undocumented_actions_count = 0

    modelfiles = os.listdir(model_dir)
    for file in modelfiles:
        if file[-5:] != ".json":
            continue

        with open(f"{model_dir}/{file}", "r") as r:
            data = json.load(r)
        
        # First check if the UID exists in botocore. If not, all operations are free game
        if data['metadata']['uid'] not in botocore.keys():
            #print(f"{data['metadata']['uid']} not found  ")
            undocumented_services_count += 1
            for operation in data['operations'].keys():
                internal = ""
                if "internalonly" in data['operations'][operation].keys():
                    internal = "internalonly"
                undocumented_actions_count += 1
                #print(f"[v]({MODELS_DIR}/{file}) - {data['metadata']['uid']}:{operation} {internal}  ")
        
        # else, if the uid's match, compare the operations
        elif data['metadata']['uid'] in botocore.keys():
            for operation in data['operations']:
                if operation not in botocore[data['metadata']['uid']]['operations'].keys():
                    internal = ""
                    if "internalonly" in data['operations'][operation].keys():
                        internal = "internalonly"
                    undocumented_actions_count += 1
                    #print(f"[v]({MODELS_DIR}/{file}) - {data['metadata']['uid']}:{operation} {internal}  ")

    print(f"Total undocumented services by uid: {undocumented_services_count}")
    print(f"Total undocumented actions by uid: {undocumented_actions_count}")


def check_botocore_dir():
    if len(sys.argv) < 2:
        print("Usage: ./scripts/compare-2-botocore.py <path to botocore>")
        exit(1)

    botocore_dir = sys.argv[1]
    if not os.path.isdir(botocore_dir):
        print("Provided path does not exist.")
        print("Usage: ./scripts/compare-2-botocore.py <path to botocore>")
        exit(2)

if __name__ == "__main__":
    main()
