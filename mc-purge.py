#!/usr/bin/env python
# -*- coding: utf-8 -*-

# v1.0a rafamiga 2017-09-29

"""
Very simple HTTP server in python.
"""
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from cgi import parse_header, parse_multipart, parse_qs
from urllib import quote,quote_plus,unquote

import SocketServer
# pip install requests
import requests
import sys, re

CONFIG_FILE = "./mc-purge.config.json"

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

    def _display_form(self):
        global msg
        global cfg

        self._set_headers()
        self.wfile.write('<html><head><title>MC PURGE</title></head><body><pre>');
        if len(msg):
            self.wfile.write('<br />' + msg + '</br />');
        self.wfile.write('<form action="/" method="POST">');
        self.wfile.write('<label for="sysid">system:&nbsp;</label>');
        self.wfile.write('&nbsp;');
        self.wfile.write('<select name="sysid">');

        for sysid in cfg:
            self.wfile.write('<option value="' + sysid + '">' + cfg[sysid]["alias"] + '</option>');

        self.wfile.write('</select>');
        self.wfile.write('&nbsp;');
        self.wfile.write('<label for="purgeurl">ściezka:&nbsp;</label>');
        self.wfile.write('<input name="purgeurl" type="text" value="" />*');
        self.wfile.write('&nbsp;');
        self.wfile.write('<input type="submit" value="Wykonaj"/>');
        self.wfile.write('</form>');
        if not len(msg):
            self.wfile.write('* - podaj ścieżkę ze znakiem &quot;/&quot; na początku.</pre></body></html>');
    
    def do_GET(self):
        global msg

        msg = ""
        self._display_form()
            
    def do_HEAD(self):
        self._set_headers()
        
    def parse_POST(self):
        ctype, pdict = parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            postvars = parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            postvars = parse_qs(
                    self.rfile.read(length), 
                    keep_blank_values=1)
        else:
            postvars = {}
        return postvars

    def do_POST(self):
        global msg
        
        msg = ""
        purgeurl = ""
        sysid = ""

        postvars = self.parse_POST()
        # print str(postvars)

        if "purgeurl" in postvars:
            purgeurl = postvars['purgeurl'][0]
        if "sysid" in postvars:
            sysid = postvars['sysid'][0]

        print "*** purgeurl='%s' sysid='%s'" % (purgeurl,sysid)

        while sysid in cfg:
            if len(purgeurl) < 3:
                msg = "BŁĄD: Ścieżka jest za krótka<br />"
                break

            if purgeurl[0] != "/":
                msg = "BŁĄD: Ścieżka musi zaczynać się od znaku &quot;/&quot;<br />"
                break


            msg = msg + "<b>[" + cfg[sysid]["alias"] + "]</b><br />"
    
            for a in cfg[sysid]["urls"]:
                url = "http://" + cfg[sysid]["urls"][a]["host"] + ":" + cfg[sysid]["urls"][a]["port"] + purgeurl
                hostname = cfg[sysid]["urls"][a]["hostname"]
                msg = msg + "* " + url + " Host: " + hostname + " ...<br />&nbsp;&nbsp;"

                try:    
                    hdrs = { "Host": hostname }
                    resp = requests.request("PURGE", url, timeout=2, headers=hdrs)

                    if resp.status_code > 299:
                        msg = msg + "<b>[NIEPOWODZENIE]</b> "
            
                    msg = msg + "[HTTP " + str(resp.status_code) + "] "

                    if hasattr(resp, "text"):
                        for l in resp.text.splitlines():
                            l.strip()
                            # print "l=%s" % l
                            m = re.match(r'^\s*<title>(.*)</title>',l)
                            if m:
                                msg = msg + m.group(1)
                            
                    msg = msg + "<br />"

                except requests.exceptions.Timeout:
                    msg = msg +  "[BŁĄD: Przekroczony czas żądania]<br />";
                except requests.exceptions.RequestException as e:
                    print "!!! exception=%s" % e
                    msg = msg + "[BŁĄD: %s]<br />" % str(e)

            break    

        self._display_form()
        
def run(server_class=HTTPServer, handler_class=S, port=3000):
    global msg
    msg = ""
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print '*** Start httpd...'
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv
    import json

    try:
        with open(CONFIG_FILE) as json_conf:
            cfg = json.load(json_conf)
    except IOError as e:
        print "!!! Błąd wczytywania pliku konfiguracyjnego '" + CONFIG_FILE + "' (%s) %s" % (e.errno, e.strerror)
        sys.exit(-1)
    except:
        raise

    reload(sys)  
    sys.setdefaultencoding("utf-8")
        
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
