#! /usr/bin/env python
# _*_ coding:utf8 _*_
# date:20170623
# author:gengyantao

# encoding: utf-8
import json
import os
import time
import sys
import logging
import urllib
import urllib2
from json import JSONDecoder

K8S_API_HOST_YZ = 'http://k8sapiyz.emarbox.com'
K8S_API_HOdST_HZ = 'http://k8sapihz.emarbox.com'
K8S_API_HOST_HT = 'http://k8sapiht.emarbox.com'
K8S_API_HOST_SH = 'http://k8sapish.emarbox.com'
K8S_API_HOST_LIST = [K8S_API_HOST_YZ, K8S_API_HOST_HZ, K8S_API_HOST_HT]
DOCKEROPS_API_HOST = '123.59.17.103:8090'
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(funcName)-10s %(lineno)d %(message)s',
                    filename='%s.log' % "k8s_rolldelete.py",
                    filemode='w')


def get_from_k8sui_pods(api_host, uri=None, ds_name=None):
    need_to_delete_pod_dict = {}
    try:
        urllibClient = urllib.urlopen("%s%s" % (api_host, uri))
        resule_str   = urllibClient.read()
        _dict = json.loads(resule_str)
        urllibClient.close()
    except Exception as e:
        logging.exception(e)
        return need_to_delete_pod_dict

    try:
        if len(_dict[u'items']) > 0:
            for item in _dict[u'items']:
                if item[u'metadata'][u'name'].find(ds_name) != -1:
                    need_to_delete_pod_dict[item[u'metadata'][u'name']] = str(item[u'status'][u'podIP'])
    except Exception as e:
        logging.exception(str(_dict))

    return need_to_delete_pod_dict


def get_from_k8sui_container_port(api_host, uri=None):
    port_list = []
    try:
        urllibClient = urllib.urlopen("%s%s" % (api_host, uri))
        resule_str   = urllibClient.read()
        _dict = json.loads(resule_str)
        urllibClient.close()
    except Exception as e:
        logging.exception(e)
        return port_list

    try:
        if type(_dict[u'spec'][u'containers']) is type([]):
            for containers in _dict[u'spec'][u'containers']:
                try:
                    port = 0
                    for item in containers[u'env']:
                        if item['name'] == 'name':
                            port = int(item['value'].split('-')[-1])
                            break
                    if port == 0:
                        if containers.has_key(u'name'):
                            port_list.append(int(containers[u'name'].split('-')[-1]))
                    else:
                        port_list.append(port)
                except Exception as e:
                    continue
        try:
            tags = _dict[u'spec'][u'containers'][0]['image'].split(':')[1]
        except Exception as e:
            raise e
    except Exception as e:
        logging.exception(str(_dict))

    return port_list,tags


def get_all_pods(api_host, ds_name):
    return get_from_k8sui_pods(api_host, '/api/v1/namespaces/default/pods/', ds_name)


def get_container_port(api_host, ds_name):
    return get_from_k8sui_container_port(api_host, '/api/v1/namespaces/default/pods/%s' % ds_name)


def post_to_dockerops(uri=None, params=None):
    try:
        requrl = "http://%s%s/" % (DOCKEROPS_API_HOST, uri)
        req = urllib2.Request(url=requrl, data=params)
        res_data = urllib2.urlopen(req)
        res = res_data.read()
        res_dict = JSONDecoder().decode(res)
        if not res_dict.has_key('msg'):
            raise Exception(res)
    except Exception as e:
        logging.exception(e)
        raise Exception(e)


def start_deploy(daemonset_name, project_tag):
    try:
        data = {'tag': project_tag,
                'dsname': daemonset_name,
                'step': 2}
        params = urllib.urlencode(data)
        post_to_dockerops('/start_deploy', params)
    except Exception as e:
        logging.exception(e)
        raise Exception(e)


def get_deploy_status(daemonset_gray_name):
    try:
        urllibClient = urllib.urlopen("http://%s/%s?dsname=%s" % (DOCKEROPS_API_HOST, 'get_deploy_status', daemonset_gray_name))
        resule_str   = urllibClient.read()
        _dict = json.loads(resule_str)
        urllibClient.close()
    except Exception as e:
        raise Exception(e)

    if _dict.has_key('error'):
        return None, _dict['error'], None, None, None
    else:
        return _dict['step'], _dict['msg'], _dict['continue_deploy'], _dict['task'], _dict['deploy_ds']


def get_ip_port(msg):
    ip_port_list = []
    try:
        for item in msg:
            ip_port_list.append(item.split(' ')[1].split(':'))
    except Exception as e:
        pass
    return ip_port_list


def update_daemonset_tags(dsname_gray, step, deploy_result):
    data = {'dsname_gray': dsname_gray,
            'step': step,
            'deploy_result': deploy_result
            }
    params = urllib.urlencode(data)

    try:
        requrl = "http://%s%s/" % (DOCKEROPS_API_HOST, '/update_deploy_status')
        req = urllib2.Request(url=requrl, data=params)
        res_data = urllib2.urlopen(req)
        res = res_data.read()
        res_dict = JSONDecoder().decode(res)
        if not res_dict.has_key('msg'):
            raise Exception(res)
    except Exception as e:
        logging.exception(e)
        raise Exception(e)


if __name__ == '__main__':
    daemonset_name = os.popen("echo $daemonset_name").read().strip('\n')
    # daemonset_name = 'yiqifa-frontearner-htgray-19120'
    # project = 'egou-apisuperf'
    # project_tag = '20170630-srcV1076-dokV3523'
    daemonset_name = daemonset_name.replace(" ", "")
    if daemonset_name == '':
        raise ValueError('daemonset_name is null')
        sys.exit(1)

    project_tag = ''
    while 1:
        time.sleep(5)
        step, msg, continue_deploy, task, dsname = get_deploy_status(daemonset_name)
        if (step is None) or (task == 1 and step == 0):
            if project_tag != '':
                print 'deploy finish'
                break
            for api_host in K8S_API_HOST_LIST:
                new_pod_dict = get_all_pods(api_host, daemonset_name)
                for pod_name, pod_ip in new_pod_dict.items():
                    pod_port_list,project_tag = get_container_port(api_host, pod_name)
            if project_tag == '':
                print "%s not found" % daemonset_name
                sys.exit(1)
            start_deploy(daemonset_name, project_tag)

        elif step in [-2, 2]:
            print "deploying"
            sys.stdout.flush()

        elif step in [-1, 0, 1]:
            if step == 0 and task == 1:
                sys.exit(0)

            ip_port_list = get_ip_port(msg)
            if len(ip_port_list) > 0:
                # print "%s-%s" % (daemonset_name.split('-')[0], daemonset_name.split('-')[1])
                print 'dsname:', dsname
                print 'images_tag:', project_tag
                for ip, port in ip_port_list:
                    print "%s:%s" % (ip, port)
                print "waiting check ip:port"
                print "if check ok ,click the url for continue http://123.59.17.103:8090/continue_deploy/?dsname_gray=%s" % daemonset_name
                sys.stdout.flush()
                while 1:
                    step, msg, continue_deploy, task, dsname = get_deploy_status(daemonset_name)
                    if continue_deploy == 1:
                        break
                    elif step == 0 and task == 1:
                        break
                    else:
                        time.sleep(2)
            if step == 0:
                print 'deploy finish'
                sys.exit(0)
            else:
                update_daemonset_tags(daemonset_name, 2, json.dumps(['autotest finish']))
            sys.stdout.flush()

        else:
            print step, msg
            sys.stdout.flush()
            sys.exit(1)
