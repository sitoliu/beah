# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import reactor
from beah.wires.internals.twadaptors import ControllerAdaptor_Backend_JSON
from beah import config

import os
import sys
import logging
import logging.handlers
log = logging.getLogger('backend')

################################################################################
# FACTORY:
################################################################################
class BackendFactory(ReconnectingClientFactory):
    def __init__(self, backend, controller_protocol, byef=None):
        self.backend = backend
        if byef:
            self.backend.proc_evt_bye = byef
        self.controller_protocol = controller_protocol

    def linfo(self, fmt, *args, **kwargs):
        l = [self.__class__.__name__]
        l.extend(args)
        log.info('%s: '+fmt, *l, **kwargs)

    ########################################
    # INHERITED METHODS:
    ########################################
    def startedConnecting(self, connector):
        self.linfo('Started to connect.')

    def buildProtocol(self, addr):
        self.linfo('Connected.  Address: %r', addr)
        self.linfo('Resetting reconnection delay')
        self.resetDelay()
        controller = self.controller_protocol()
        controller.add_backend(self.backend)
        return controller

    def clientConnectionLost(self, connector, reason):
        self.linfo('Lost connection.  Reason: %s', reason)
        self.backend.set_controller()
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.linfo('Connection failed. Reason: %s', reason)
        self.backend.set_controller()
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

def log_handler(log_file_name):
    conf = config.config()
    # Create a directory for logging and check permissions
    lp = conf.get('DEFAULT', 'LOG_PATH') or "/var/log"
    if not os.access(lp, os.F_OK):
        try:
            os.makedirs(lp, mode=0755)
        except:
            print >> sys.stderr, "ERROR: Could not create %s." % lp
            # FIXME: should create a temp file
            raise
    elif not os.access(lp, os.X_OK | os.W_OK):
        print >> sys.stderr, "ERROR: Wrong access rights to %s." % lp
        # FIXME: should create a temp file
        raise

    #lhandler = logging.handlers.RotatingFileHandler(lp + "/" + log_file_name,
    #        maxBytes=1000000, backupCount=5)
    lhandler = logging.FileHandler(lp + "/" + log_file_name)
    # FIXME: add config.option?
    if sys.version_info[0] == 2 and sys.version_info[1] <= 4:
        fmt = ': %(levelname)s %(message)s'
    else:
        fmt = ' %(funcName)s: %(levelname)s %(message)s'
    lhandler.setFormatter(logging.Formatter('%(asctime)s'+fmt))
    log.addHandler(lhandler)

    lhandler = logging.handlers.SysLogHandler()
    lhandler.setFormatter(logging.Formatter('%(asctime)s %(name)s'+fmt))
    lhandler.setLevel(logging.ERROR)
    log.addHandler(lhandler)

def start_backend(backend, host=None, port=None,
        adaptor=ControllerAdaptor_Backend_JSON,
        byef=None):
    conf = config.config()
    host = host or conf.get('BACKEND', 'INTERFACE')
    port = port or int(conf.get('BACKEND', 'PORT'))
    if not config.parse_bool(conf.get('BACKEND', 'DEVEL')):
        ll = logging.WARNING
    else:
        ll = logging.DEBUG
    log.setLevel(ll)
    reactor.connectTCP(host, port, BackendFactory(backend, adaptor, byef))

################################################################################
# TEST:
################################################################################
if __name__=='__main__':
    from beah.core.backends import PprintBackend
    from beah.core import command

    class DemoOutAdaptor(ControllerAdaptor_Backend_JSON):

        def linfo(self, fmt, *args, **kwargs):
            l = [self.__class__.__name__]
            l.extend(args)
            log.info('%s: '+fmt, *l, **kwargs)

        def connectionMade(self):
            self.linfo("I am connected!")
            ControllerAdaptor_Backend_JSON.connectionMade(self)
            self.proc_cmd(self.backend, command.PING("Hello everybody!"))

        def connectionLost(self, reason):
            self.linfo("I was lost!")

        def lineReceived(self, data):
            self.linfo('Data received.  Data: %r', data)
            ControllerAdaptor_Backend_JSON.lineReceived(self, data)

    class DemoPprintBackend(PprintBackend):
        def set_controller(self, controller=None):
            PprintBackend.set_controller(self, controller)
            if controller:
                self.controller.proc_cmd(self, command.ping("Are you there?"))

    log_handler('beah_demo_backend.log')
    start_backend(DemoPprintBackend(), adaptor=DemoOutAdaptor, byef=lambda evt: reactor.stop())
    reactor.run()

