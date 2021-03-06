# -*- test-case-name: beah.filters.test.test_cmdfilter -*-

# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Red Hat, Inc.
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

import exceptions
import re
import os.path
import shlex
from sys import stderr
from optparse import OptionParser
from beah.core import command, new_id

class CmdFilter(object):

    __ignore_re = re.compile('^\s*(.*?)\s*(#.*)?$')
    __cmd_re = re.compile('^(\S+).*$')
    __args_re = re.compile('^\S+(?:\s+(.*?))?$')
    __varre = re.compile('''^([a-zA-Z_][a-zA-Z0-9_]*)=(.*)$''')

    __run_opt = OptionParser()
    __run_opt.add_option("-n", "--name", action="store", dest="name",
            help="task name")
    __run_opt.add_option("-D", "--define", action="append", dest="variables",
            metavar="VARIABLES",
            help="VARIABLES specify list of overrides.")

    def __init__(self):
        self.__handlers = {}

    def add_handler(self, handler, help='', *cmds):
        for cmd in cmds:
            self.__handlers[cmd] = (handler, help or handler.__doc__)

    # FIXME: this could block(?)
    # In case of cmd filter it is not crucial(?)
    def echo(self, msg):
        print msg
        return None

    def echoerr(self, msg):
        print >> stderr, msg
        return None

    def proc_cmd_quit(self, cmd, cmd_args):
        raise exceptions.StopIteration("quit")
    proc_cmd_q = proc_cmd_quit

    def proc_cmd_help(self, cmd, cmd_args):
        return self.echo(self.usage_msg())
    proc_cmd_h = proc_cmd_help

    def proc_cmd_ping(self, cmd, cmd_args):
        if cmd_args:
            message = ' '.join(cmd_args)
        else:
            message = None
        return command.ping(message)

    def proc_cmd_PING(self, cmd, cmd_args):
        if cmd_args:
            message = ' '.join(cmd_args)
        else:
            message = None
        return command.PING(message)

    def proc_cmd_flush(self, cmd, cmd_args):
        return command.flush()

    def proc_cmd_dump(self, cmd, cmd_args):
        return command.Command('dump')

    def proc_cmd_kill(self, cmd, cmd_args):
        return command.kill()

    def proc_cmd_run(self, cmd, cmd_args):
        opts, args = self.__run_opt.parse_args(cmd_args)
        if len(args) < 1:
            raise exceptions.RuntimeError('file to run must be provided.')
        variables = {}
        if opts.variables:
            for pair in opts.variables:
                key, value = self.__varre.match(pair).group(1, 2)
                variables[key] = value
        if cmd == 'runthis':
            f = open(os.path.abspath(args[0]), 'r')
            try:
                script = f.read()
                return command.run_this(script, name=opts.name or args[0],
                        env=variables, args=args[1:])
            finally:
                f.close()
        else:
            return command.run(os.path.abspath(args[0]), name=opts.name or args[0],
                    env=variables, args=args[1:])
    proc_cmd_r = proc_cmd_run
    proc_cmd_runthis = proc_cmd_run

    def proc_line(self, data):
        args = shlex.split(data, True)
        if not args:
            return None
        cmd = args[0]
        f = getattr(self, "proc_cmd_"+cmd, None)
        if f:
            return f(cmd=cmd, cmd_args=args[1:])
        return self.echoerr("Command %s is not implemented. Input line: %s" % (cmd, data))

    def usage_msg(self):
        return """\
ping [MESSAGE]\n\tping a controller, response is sent to issuer only.
PING [MESSAGE]\n\tping a controller, response is broadcasted to all backends.
run [OPTS] TASK [ARGS]\nr TASK\trun a task. TASK is an executable.
\tOptions:
\t-n --name=NAME -- task name
\t-D --define VARIABLE=VALUE -- define environment variable VARIABLE.
runthis [OPTS] TASK [ARGS]\n\trun a task. TASK is an executable (a script).
\tThis command takes same options as run but sends file content as a string.
\tUseful to run a script on a remote machine.
kill\tkill a controller.
dump\tinstruct controller to print a diagnostics message on stdout.
flush\twrite memory cached data to disk.
quit\nq\tclose this backend.
help\nh\tprint this help message.
"""

