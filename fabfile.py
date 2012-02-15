from fabric.api import (puts,env,cd,settings,prompt,open_shell)
from fabric.api import local as wrapped_local
from fabric.api import run as wrapped_run
from fabric.colors import red,green,yellow,magenta

env.user = 'ubuntu'
env.hosts = ['ec2-23-20-45-108.compute-1.amazonaws.com',]
env.http_port = '8180'
env.CSPACE_JEESERVER_HOME = '/usr/local/share/apache-tomcat-6.0.33'
env.service_identifier = 'wac-collectionspace'

project_dir = '/home/ubuntu/src/v2.0/'
minibuild_dir = '/home/ubuntu/src/minibuild/'

rrun   = lambda string,*args,**kwargs: wrapped_run(string.format(**env), *args,**kwargs)
llocal = lambda string,*args,**kwargs: wrapped_local(string.format(**env), *args,**kwargs)

def stop_server():
    "runs shutdown.sh -force and kills tomcat"
    with settings(warn_only=True):
        rrun('source ~/.bashrc &&  {CSPACE_JEESERVER_HOME}/bin/shutdown.sh -force', pty=False)
    pid = get_pid()
    if not pid:
        print(red("no java process found"))
        return

    pids = pid.split('\r\n')
    if len(pids) > 1:
        puts(magenta("multiple pids found: " + ','.join(pids)))
        puts(magenta("kill them yourself (exit when done)"))
        open_shell()
    else:
        puts(yellow("stopping pid " + pid))
        with settings(warn_only=True):
            rrun('kill -9 ' + pid)
    rm_pid()

def get_pid():
    "pid of java program (assuming cspace server)"
    pid = rrun("ps ww -C java | grep {service_identifier} | awk '{{print$1}}'",True)
    puts(green("pid = " + pid))
    return pid

def rm_pid():
    rrun('touch {CSPACE_JEESERVER_HOME}/bin/tomcat.pid')
    rrun('rm {CSPACE_JEESERVER_HOME}/bin/tomcat.pid')

def start_server():
    "start collectionspace"
    pid = get_pid()
    if pid:
        puts(yellow('server appears to be running; run stop_server first'))
        return 
    rrun('source ~/.bashrc && {CSPACE_JEESERVER_HOME}/bin/startup.sh -dservice.identifier={service_identifier}', pty=False)
    pid = get_pid()

def cat_log():
    "see tail of catalina.out"
    rrun("tail {CSPACE_JEESERVER_HOME}/logs/catalina.out", pty=False)

def _build():
    rrun('ant undeploy deploy', pty=False)

def hit_init():
    "login to collectionspace and GET tenant init to reload the configs"
    env.cookie_file = "cookies.txt"
    env.login_userid = 'admin@walkerart.org'
    env.login_password = prompt("enter password for {}:".format(env.login_userid))
    llocal("""\
          wget -q --keep-session-cookies --save-cookies {cookie_file} \
          --post-data "userid={login_userid}&password={login_password}" \
          http://{host_string}:{http_port}/collectionspace/tenant/walkerart/login \
          -O /dev/null \
          """.format(**env))

    cookie = open(env.cookie_file).readlines().pop()
    if "CSPACESESSID" in cookie:
        print(green("logged in successfully"))
    else:
        print(red("not logged in! wrong password?"))
        return 

    llocal("""\
          wget --keep-session-cookies --load-cookies {cookie_file} \
          http://{host_string}:{http_port}/collectionspace/tenant/walkerart/init \
          -O - \
          """.format(**env))

    llocal('rm ' + env.cookie_file)


def _git_pull():
    rrun('git pull origin custom')
        
def deploy(layer='application'):
    "pull updates from git origin and load 'em up"
    directory = "{path}/{layer}".\
                  format(path=minibuild_dir,  layer=layer)
    with cd(minibuild_dir):
        _git_pull()
    stop_server()
    with cd(directory):
        _build()
    start_server()
        
