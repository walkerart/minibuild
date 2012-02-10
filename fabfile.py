from fabric.api import *

env.user = 'ubuntu'
env.hosts = ['col.walkerart.org',]
project_dir = '/home/ubuntu/src/v2.0/'
minibuild_dir = '/home/ubuntu/src/minibuild/'


def stop_server():
    "tomcat does not stop in time so we need to HUP it"
    with settings(warn_only=True):
        run('$CSPACE_JEESERVER_HOME/bin/shutdown.sh')
    pid = run("ps -C java | awk '{getline; print$1}'",True)
    run('kill -HUP ' + pid)

def start_server():
    run('$CSPACE_JEESERVER_HOME/bin/startup.sh')

def build():
    run('ant undeploy deploy')        

def git_pull():
    run('git pull origin custom')
        
def upgrade():
    with cd(project_dir):
        git_pull()
        stop_server()
        build()
        start_server()
        
def deploy(layer='application'):
    directory = "{path}/tenant-customizations-v2.0/{layer}".\
                  format(path=minibuild_dir,  layer=layer)
    stop_server()
    with cd(directory):
        build()
    start_server()
        
