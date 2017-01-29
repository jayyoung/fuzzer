#!/usr/bin/env python
import json
import urllib2
import urllib
import re
import argparse
import random
from threading import Thread, Timer
import Queue
import time
import sys, traceback, os
import ssl


OUTPUT_DELIMITER = "\t"

class Fuzzer():
    def __init__(self,ports,target,throttle,timeout):
        print("-- Fuzzer Active --")

        if(ports is not None):
            self.port_list = self.read_ports_file(ports)
        else:
            self.port_list = range(0,65535)

        self.request_timeout = timeout
        print("Num ports to try: " + str(len(self.port_list)))
        print("Target: " + str(target))
        print("Throttle: " + str(throttle))
        print("PORT"+OUTPUT_DELIMITER+"SUCCESS"+OUTPUT_DELIMITER+"CODE"+OUTPUT_DELIMITER+"TITLE"+OUTPUT_DELIMITER+"NOTES")
        self.launch_requests(throttle,target,self.port_list,self.request_timeout)

    # uses a regular expression to just extract the title tag from
    # the page we get back. slightly hacky but no need for any
    # deeper parsing if this is all we're doing
    def return_title_tag_from_page(self,page_html):
        # look for any string contained within these title tags
        rex = re.search('<title>(.*?)</title>',page_html)
        out = "EMPTY"
        if(rex is None):
            return out
        else:
            out = rex.group(0)
        return out

    def read_ports_file(self,filename):
        with open(filename) as f:
            ports = [line.rstrip('\n') for line in open(filename)]
        ports = map(int, [x for x in ports if x])
        return ports


    def get_random_user_agent(self):
        user_agents = []
        user_agents.append('Mozilla/5.0 (Windows NT 6.1; Win64; x64)')
        user_agents.append('Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36')
        user_agents.append('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36')
        user_agents.append('Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0')
        user_agents.append('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0')
        user_agents.append('Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko')
        return random.choice(user_agents)

    def launch_requests(self,init_threads,url,ports,to=2):
        q = Queue.Queue()
        active = True
        threads_to_create = init_threads
        already_printed = []
        cur_port_idx = 0
        cur_threads = []
        while(active is True):
            for i in range(init_threads):
                if(cur_port_idx >= len(ports)):
                    active = False
                    break
                cur_port = ports[cur_port_idx]
                thr = Thread(target=self.make_request, args=(url,cur_port,to,q))
                thr.start()
                cur_threads.append(thr)
                cur_port_idx+=1

            time.sleep(1)

            cache = list(q.queue)
            for k in cache:
                if(k not in already_printed):
                    print(k)
                    already_printed.append(k)
        threads_still_alive = True
        while(threads_still_alive is True):
            any_alive = False
            for t in cur_threads:
                if(t.isAlive()):
                    any_alive = True
            if(any_alive is False):
                break

        cache = list(q.queue)
        if(active is False):
            for k in cache:
                if(k not in already_printed):
                    print(k)
                    already_printed.append(k)


    def make_request(self,url,port,to,queue):
        try:
            headers = {'User-Agent': self.get_random_user_agent()}
            data = ""
            req = urllib2.Request(url+":"+str(port), data, headers)
            gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            response = urllib2.urlopen(req,timeout=to,context=gcontext)
            the_page = response.read()
            the_code = response.getcode()
            queue.put(str(port) + OUTPUT_DELIMITER + "true" + OUTPUT_DELIMITER + str(the_code) + OUTPUT_DELIMITER + self.return_title_tag_from_page(the_page)+OUTPUT_DELIMITER+"N/A")
        except Exception as e:
            queue.put(str(port) + OUTPUT_DELIMITER + "false" + OUTPUT_DELIMITER + "N/A" + OUTPUT_DELIMITER + "NONE"+OUTPUT_DELIMITER+str(e))
            #queue.put(e)
            #print(e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fuzz Some Domains')
    parser.add_argument('-ports', metavar='-P', type=str, nargs='+',
                       help='The file containing all your ports. Will be read line-by-line')
    parser.add_argument('-target', metavar='-T', type=str, nargs='+',
                       help='The target domain to investigate. EXCLUDING the trailing slash. So must be in the format: http://somewebsite.com')
    parser.add_argument('-throttle', metavar='-R', type=int, nargs='+',
                       help='The desired throttle, specified as max number of attempts per second.')
    parser.add_argument('-timeout', metavar='-O', type=int, nargs='+',
                       help='The timeout period after which we consider an attempt at a port to have failed')

    args = parser.parse_args()

    print("Program Arguments:")
    print("-ports filename\n\tthe file name in this directory containing the ports you want to try. This is optional, and if so the system will scan all ports if it is left out.")
    print("-target url\n\tthe target URL to investigate, in the format: http://somewebsite.com")
    print("-throttle num\n\tthe target throttle, the maximum number of requests to the server in a 1 second time window.")
    print("-timeout num\n\tthe timeout period, in seconds, after which we consider an attempt on a target port failed")
    print("-EXAMPLE USAGE- scan from wordlist\n\t python fuzzer.py -ports ports.txt -target http://reddit.com -throttle 20 -timeout 2")
    print("-EXAMPLE USAGE- scan all ports\n\t python fuzzer.py -target http://reddit.com -throttle 20 -timeout 2")


    if(args.target is None or args.throttle is None or args.timeout is None):
        print("Invalid Arguments")
        sys.exit(1)

    p = args.ports
    if(p is not None):
        p = args.ports[0]
    try:
        f = Fuzzer(p,args.target[0],args.throttle[0],args.timeout[0])
    except KeyboardInterrupt:
        print("-- Fuzzing Cancelled By User --")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
