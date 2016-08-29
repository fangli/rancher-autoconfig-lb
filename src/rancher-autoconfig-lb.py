#!/usr/bin/env python


import os
import json
import time
import re
import sys
import requests


try:
    CATTLE_URL = os.environ["CATTLE_URL"]
    CATTLE_ACCESS_KEY = os.environ["CATTLE_ACCESS_KEY"]
    CATTLE_SECRET_KEY = os.environ["CATTLE_SECRET_KEY"]
except:
    print >> sys.stderr, "You must set label 'io.rancher.container.create_agent: true' and 'io.rancher.container.agent.role: environment' for this service"
    time.sleep(15)
    sys.exit(1)


try:
    r = requests.get('%s/self/container/labels/autoconfig.proxy.service_name' % META_URL)
    r.raise_for_status()
    TARGET_SERVICE = r.text
except:
    print >> sys.stderr, "You must set label autoconfig.proxy.service_name as target load balancer name"
    time.sleep(15)
    sys.exit(1)


LAST_MAPPING = []
META_URL = 'http://rancher-metadata.rancher.internal/2015-12-19'


class RancherProxy(object):

    def __init__(self):
        self.services = []
        self.envid = None
        self.__get_basic_info()

    def __get_basic_info(self):
        uuid = requests.get('%s/self/stack/environment_uuid' % META_URL).text

        r = requests.get(
            '%s/projects?uuid=%s' % (CATTLE_URL, uuid),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            auth=(CATTLE_ACCESS_KEY, CATTLE_SECRET_KEY),
        )
        if r.status_code != 200:
            raise Exception("Failed to get environment ID: %s" % r.text)
        self.envid = r.json()['data'][0]['id']

        r = requests.get(
            '%s/projects/%s/services' % (CATTLE_URL, self.envid),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            auth=(CATTLE_ACCESS_KEY, CATTLE_SECRET_KEY),
        )
        if r.status_code != 200:
            raise Exception("Failed to get service: %s" % r.text)
        self.services = r.json()['data']

    def __check_domains(self, domains):
        for d in domains:
            if not re.match(r'^[a-zA-Z0-9=:/\.\-\_]+$', d):
                raise Exception('Domains format are invalid: %s' % d)

    def get_domain_map(self):
        payload = []
        for service in self.services:
            try:
                if (service['type'] == 'service') and (service['state'] not in ('deactivating', 'inactive', 'removed', 'removing')) and ('domain' in service['launchConfig']['labels']):
                    domains = service['launchConfig']['labels']['domain'].replace(' ', '').replace(';', ',').split(',')
                    self.__check_domains(domains)
                    payload.append({'serviceId': service['id'], 'ports': domains})
            except Exception, e:
                print >> sys.stderr, 'Error when parsing domains: ' + str(e) + ', ' + str(service)

        return payload

    def get_target_lb(self):
        for service in self.services:
            if service['name'] == TARGET_SERVICE and service['type'] == 'loadBalancerService':
                return service['id']
        raise Exception('Target load balancer not found: %s' % TARGET_SERVICE)

    def update_proxy(self, proxy_id, mapping):
        ret = requests.post(
            '%s/projects/%s/loadbalancerservices/%s/?action=setservicelinks' % (CATTLE_URL, self.envid, proxy_id),
            data=json.dumps({'serviceLinks': mapping}),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            auth=(CATTLE_ACCESS_KEY, CATTLE_SECRET_KEY),
        )
        if ret.status_code != 200:
            raise Exception("Update load balancer failed. Request: %s, Response: %s" % (json.dumps(mapping), ret.text))


def parse_change(old, new):
    add = []
    remove = []
    update = []
    _old = dict([(x['serviceId'], x['ports']) for x in old])
    _new = dict([(x['serviceId'], x['ports']) for x in new])
    for k in (set(_new) - set(_old)):
        add.append(','.join(_new[k]))
    for k in (set(_old) - set(_new)):
        remove.append(','.join(_old[k]))
    for k in (set(_new) & set(_old)):
        if set(_new[k]) != set(_old[k]):
            update.append('%s -> %s' % (','.join(_old[k]), ','.join(_new[k])))
    return (add, remove, update)


def update():
    global LAST_MAPPING
    rp = RancherProxy()
    target_lb = rp.get_target_lb()
    mapping = rp.get_domain_map()
    add, remove, update = parse_change(LAST_MAPPING, mapping)
    if (len(add) == 0) and (len(remove) == 0) and (len(update) == 0):
        return
    else:
        print "ADD: %s\nREMOVE: %s\nUPDATE: %s" % ('; '.join(add), '; '.join(remove), '; '.join(update))
        rp.update_proxy(target_lb, mapping)
        LAST_MAPPING = mapping


def main():
    while True:
        try:
            update()
        except Exception, e:
            print >> sys.stderr, 'System error: ' + str(e)

        time.sleep(10)


if __name__ == '__main__':
    main()
