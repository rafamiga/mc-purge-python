#!/usr/bin/env python
# -*- coding: utf-8 -*-

# v2.0 rafamiga 2017-09-29; 2017-12-03

"""
Very simple HTTP server in python.
Install:
sudo apt-get install python-pip
sudo pip install python-varnish==0.1.2 # python 2.7
"""
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from cgi import parse_header, parse_multipart, parse_qs
from urllib import quote,quote_plus,unquote
import urlparse

# pip install python-varnish==0.2.1
from varnish import VarnishManager as varnish_manager
import SocketServer
# pip install requests
import requests
import sys, re

CONFIG_FILE = "./mc-purge.config.json"

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Security-Policy', "default-src 'self' 'unsafe-inline';")
        self.end_headers()

    def _display_form(self):
        global msg
        global cfg
        global getid

        self._set_headers()
        self.wfile.write('<html><head><title>MC  czyszczenie treści</title>');
        self.wfile.write('<style type="text/css">span.bred{color:red;font-weight:bold;}</style>');
        self.wfile.write('</head><body>');
        self.wfile.write('<script type="text/javascript">function rPage(id){document.location.href="/?id="+id.value;}</script>');
        self.wfile.write('<pre>');
        if len(msg):
            self.wfile.write('<br />' + msg + '</br />');
        self.wfile.write('<form action="/id=' + str(getid) + '" method="POST">');
        self.wfile.write('<label for="sysid">system:&nbsp;</label>');
        self.wfile.write('&nbsp;');
        self.wfile.write("<select name=\"sysid\" onchange='rPage(this)'>");
        self.wfile.write('<option> Wybierz </option>');

        for sysid in cfg:
            self.wfile.write('<option value="' + sysid + '"');
            if getid == int(sysid):
#                print "id selected = %d" % getid
                self.wfile.write(' selected');
            self.wfile.write('>' + cfg[sysid]["alias"]);
            self.wfile.write('</option>');

        self.wfile.write('</select>');

        if (getid > 0):
            self.wfile.write('<br />Hostname: <span class="bred">' + cfg[str(getid)]["hostname"] + '</span>');
            self.wfile.write('<br />');
            self.wfile.write('<label for="purgeurl">ściezka lub regexp:&nbsp;</label>');
            self.wfile.write('<input name="purgeurl" type="text" value="" />');
            self.wfile.write('&nbsp;');
            self.wfile.write('<input type="submit" value="  Wykonaj  "/>');
            self.wfile.write('</form>');
    	    if not len(msg):
                self.wfile.write('Legenda:<br /><ul><li>podaj ścieżkę ze znakiem &quot;/&quot; na początku.</li>')
                self.wfile.write('<li>przykład: podanie <span class="bred">/cyfryzacja/</span> wykasuje z cache wszystkie adresy rozpoczynające się od /cyfryzacja/</li>')
                self.wfile.write('<li>przykład: <span class="bred">/.*\.css.*</span> wykasuje <u>wszystkie</u> pliki arkuszy stylu (regexp)</li>')
                self.wfile.write('</pre></body></html>')

            for a in cfg[str(getid)]["endpoint"]:
                vmadm = str(cfg[str(getid)]["endpoint"][a]["adm"]);
                vmsecret = cfg[str(getid)]["endpoint"][a]["secret"]
                print "getid=%d vmadm=%s vmsecret=%s" % (getid, vmadm, vmsecret)
                manager = varnish_manager((vmadm,))
                try:
                    ok = manager.run('ping',secret=vmsecret)
                    ok = manager.run('ban.list',secret=vmsecret)
                    print ok
                except:
                    print "not ok"
                    

    def get_getid(self):
        global getid
        
        getid = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('id', None)
        try:
            getid = int(getid[0])
        except:
            getid = 0
        print "getid=%s" % getid
    
    def do_GET(self):
        global msg
        global getid
        
        getid = 0

        if (self.path == "/favicon.ico"):
            self.send_response(410)
            self.end_headers()
        else:
            self.get_getid()
            msg = ""
            self._display_form()
            
    def do_HEAD(self):
        self._set_headers()
        
    def parse_POST(self):
        global getid

        self.get_getid()
        
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
    
            for a in cfg[sysid]["endpoint"]:
                vm = varnish.VarnishManager(cfg[sysid]["endpoint"][a]["adm"])
                print vm
                
                url = "http://" + cfg[sysid]["endpoint"][a]["host"] + ":" + cfg[sysid]["endpoint"][a]["port"] + purgeurl
                hostname = cfg[sysid]["hostname"]
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

#    for sysid in cfg:
#        for e in cfg[sysid]["endpoint"]:
#            print 'adm='+cfg[sysid]["endpoint"][e]["adm"]

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
