from fabric.api import (run,puts,local,env,cd,settings,prompt,open_shell)
from fabric.colors import red,green,yellow,magenta

env.user = 'ubuntu'
# env.hosts = ['col.walkerart.org',] #waiting for internal dns
env.hosts = ['ec2-23-20-45-108.compute-1.amazonaws.com',]
env.http_port = '8180'
project_dir = '/home/ubuntu/src/v2.0/'
minibuild_dir = '/home/ubuntu/src/minibuild/'
CSPACE_JEESERVER_HOME = '/usr/local/share/apache-tomcat-6.0.33'

def stop_server():
    "runs shutdown.sh -force and kills tomcat"
    with settings(warn_only=True):
        run('source ~/.bashrc && ' + CSPACE_JEESERVER_HOME+'/bin/shutdown.sh -force', pty=False)
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
            run('kill -9 ' + pid)
    rm_pid()

def get_pid():
    "pid of java program (assuming cspace server)"
    pid = run("ps -C java | grep java | awk '{print$1}'",True)
    puts(green("pid = " + pid))
    return pid

def rm_pid():
    run('touch '+ CSPACE_JEESERVER_HOME +'/bin/tomcat.pid')
    run('rm '+ CSPACE_JEESERVER_HOME +'/bin/tomcat.pid')

def start_server():
    "start collectionspace"
    pid = get_pid()
    if pid:
        puts(yellow('server appears to be running; run stop_server first'))
        return 
    run('source ~/.bashrc && '+CSPACE_JEESERVER_HOME+'/bin/startup.sh', pty=False)
    pid = get_pid()

def cat_log():
    "see tail of catalina.out"
    run("tail "+CSPACE_JEESERVER_HOME+"/logs/catalina.out", pty=False)

def _build():
    run('ant undeploy deploy', pty=False)

def hit_init():
    "login to collectionspace and GET tenant init to reload the configs"
    env.cookie_file = "cookies.txt"
    env.login_userid = 'admin@walkerart.org'
    env.login_password = prompt("enter password for {}:".format(env.login_userid))
    local("""\
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

    local("""\
          wget --keep-session-cookies --load-cookies {cookie_file} \
          http://{host_string}:{http_port}/collectionspace/tenant/walkerart/init \
          -O - \
          """.format(**env))

    local('rm ' + env.cookie_file)


def _git_pull():
    run('git pull origin custom')
        
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
        
