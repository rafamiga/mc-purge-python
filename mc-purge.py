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
from varnish import VarnishManager, VarnishHandler
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
        self.wfile.write('<form action="/?id=' + str(getid) + '" method="POST">');
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
            self.wfile.write('<br />Hostname: <b>' + cfg[str(getid)]["hostname"] + '</b> (id=%d)' % (getid));
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
                self.wfile.write('<li>UWAGA! Jeżeli backend jest w stanie <span class="bred">SICK</span> i nastąpi usunięcie treści zostanie ona usunięta bezwarunkowo, a żądania do niej się odnoszące zakończą się błędem 503.</li>');
                self.wfile.write('</ul>')

            self.wfile.write('<hr />Status:');
            
            for a in cfg[str(getid)]["endpoint"]:
                vstatus = '<br />'

                vmadm = str(cfg[str(getid)]["endpoint"][a]["adm"]);
                vmsecret = cfg[str(getid)]["endpoint"][a]["secret"]

                vstatus += 'Cache <b>%s</b><blockquote>' % (vmadm)

#                print "getid=%d vmadm=%s vmsecret=%s" % (getid, vmadm, vmsecret)

                vm = VarnishManager((vmadm,))

                try:
                    ok = vm.run('ping',secret=vmsecret)
                    vstatus += '[PING OK]'
#                    print "ret=%s" % '<br />'.join(map(str, ok[0][0]))

                    ok = vm.run('status',secret=vmsecret)
                    vstatus += '<br />%s' % (''.join(map(str, ok[0][0])))

                    ok = vm.run('backend.list',secret=vmsecret)
                    bstatus = ''.join(map(str, ok[0][0]))
                    sick = 0
                    if re.search(' sick ',bstatus):
                        sick = 1
                    
                    if sick:
                        bstatus = '<span class="bred">' + bstatus + '</span>'
                    vstatus += bstatus

                    vstatus += '<form action="/?id=' + str(getid) + '" method="POST">'
                    vstatus += '<input type="hidden" name="sysid" value="' + str(getid) + '">'
                    vstatus += '<input type="hidden" name="backend_'
                    vstatus += "on" if sick else "off"
                    vstatus += '" value="' + a + '">'
                    vstatus += '<input type="submit" value="'
                    vstatus += "WŁĄCZ" if sick else "wyłącz"
                    vstatus += '"></form>'
                    
                    ok = vm.run('ban.list',secret=vmsecret)
                    skipline = 0
                    for l in ''.join(map(str, ok[0][0])).split('\n'):
                        if re.search(r'C\s*$',l):
                            skipline += 1
                        else:
                            vstatus += '<br />' + l                        

                    if skipline:
                        vstatus += '(liczba ukrytych zleceń wykonanych=%d)' % skipline

                except Exception as e:
                    print "!!! not ok e=%s" % e
                    vstatus += '<br /><span class="bred">NASTĄPIŁ BŁAD "%s"</span>' % e
                
                self.wfile.write(vstatus + "</blockquote>");

            self.wfile.write('</pre></body></html>')

    def get_getid(self):
        global getid
        
        getid = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('id', None)

        try:
            getid = int(getid[0])
        except:
            getid = 0
#        print "getid=%s" % getid
    
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
        global getid
        
        msg = ''
        purgeurl = ''
        sysid = ''
        off = ''
        backend_mng = ()
        
        postvars = self.parse_POST()
        # print str(postvars)

        if "sysid" in postvars:
            sysid = postvars['sysid'][0]
        if "purgeurl" in postvars:
            purgeurl = postvars['purgeurl'][0]

        msg = msg + "<b>[" + cfg[sysid]["alias"] + "]</b><br />"

        if "backend_off" in postvars:
            backend_mng = (postvars['backend_off'][0],False)

        if "backend_on" in postvars:
            backend_mng = (postvars['backend_on'][0],True)

        # management backendu
	if len(backend_mng) == 2:
            print "*** backend='%s' akcja='%s' sysid='%s'" % (backend_mng[0],str(backend_mng[1]),sysid)
            
            for a in cfg[sysid]["endpoint"]:
                if backend_mng[0] == a:
                    msg += 'Zlecenie <b>' + ('włączenia' if backend_mng[1] else 'WYŁĄCZENIA') + '</b> serwera cache: %s<br />' % a

                    vmadm = str(cfg[str(getid)]["endpoint"][a]["adm"]);
                    vmsecret = cfg[str(getid)]["endpoint"][a]["secret"]
                    msg += '>>>%s' % (vmadm)
                    vm = VarnishManager((vmadm,))

                    try:
                        ok = vm.run('backend.set.health','boot.default1','probe' if backend_mng[1] else 'sick',secret=vmsecret)
                        msg += '<br />%s' % (''.join(map(str,ok[0][0]))) + '<br />'
                        
                    except Exception as e:
                        print "!!! not ok e=%s" % e
                        msg += '<br /><span class="bred">NASTĄPIŁ BŁAD "%s"</span>' % e
                    
        # nic więcej nie robimy, uniwersalny koniec metod innych niż purgeurl
        if len(purgeurl) < 1:
            self._display_form()
            return True
    
        ### reszta to PURGE/BAN ###

        print "*** purgeurl='%s' sysid='%s'" % (purgeurl,sysid)

        while sysid in cfg:
            if len(purgeurl) < 3:
                msg = "BŁĄD: Ścieżka jest za krótka<br />"
                break

            if purgeurl[0] != "/":
                msg = "BŁĄD: Ścieżka musi zaczynać się od znaku &quot;/&quot;<br />"
                break

            for a in cfg[sysid]["endpoint"]:

#                vmadm = str(cfg[sysid]["endpoint"][a]["adm"]);
#                vmsecret = cfg[sysid]["endpoint"][a]["secret"]
#                vmadm = VarnishManager((vmadm,))

#                try:
#                    ok = vmadm.run('ban','req.http.host == %s && req.url ~ %s' % (cfg[sysid]["hostname"],purgeurl),secret=vmsecret)
#                    msg = msg + '<br />%s' % (''.join(map(str,ok[0][0])))
#                except Exception as e:
#                    msg += '<br /><span class="bred">NASTĄPIŁ BŁAD "%s"</span>' % e
#                    raise

#            break

                url = "http://" + cfg[sysid]["endpoint"][a]["host"] + ":" + cfg[sysid]["endpoint"][a]["port"] + purgeurl
                hostname = cfg[sysid]["hostname"]
                msg = msg + "* " + url + " Host: " + hostname + " ...<br />&nbsp;&nbsp;"

                try:    
                    hdrs = { "Host": hostname }
#                    resp = requests.request("PURGE", url, timeout=2, headers=hdrs)
                    resp = requests.request("XBAN", url, timeout=2, headers=hdrs)

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
        return True
        
def run(server_class=HTTPServer, handler_class=S, port=3000):
    global msg
    msg = ""

    dir(VarnishManager)
#    for sysid in cfg:
#        for e in cfg[sysid]["endpoint"]:
#            print 'adm='+cfg[sysid]["endpoint"][e]["adm"]

    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print '*** Start httpd ' + str(server_address) + ' ...'
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
