from fabric.api import (puts,env,cd,settings,open_shell, hosts)
from fabric.api import local as wrapped_local
from fabric.api import run as wrapped_run
from fabric.colors import red,green,yellow,magenta
from lxml import objectify
from BeautifulSoup import BeautifulStoneSoup
import time
env.user = 'ubuntu'
env.hosts = ['ec2-23-20-45-108.compute-1.amazonaws.com',]
env.http_port = '8180'
env.CSPACE_JEESERVER_HOME = '/usr/local/share/apache-tomcat-6.0.33'
env.CATALINA_PID="/usr/local/share/apache-tomcat-6.0.33/bin/tomcat.pid"
env.service_identifier = 'wac-collectionspace'
env.tenant = 'walkerart'
env.login_userid = 'admin@walkerart.org'
env.password = 'Administrator'
services_dir = '/home/ubuntu/src/services/'
minibuild_dir = '/home/ubuntu/src/minibuild/'

rrun   = lambda string,*args,**kwargs: wrapped_run(string.format(**env), *args,**kwargs)
llocal = lambda string,*args,**kwargs: wrapped_local(string.format(**env), *args,**kwargs)

def stop_server():
    "runs shutdown.sh -force and kills tomcat"
    with settings(warn_only=True):
        rrun('source ~/.bashrc &&  {CSPACE_JEESERVER_HOME}/bin/shutdown.sh -force')
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

def start_server(func=rrun):
    "start collectionspace"
    pid = get_pid(func)
    if pid:
        puts(yellow('server appears to be running; run stop_server first'))
        return 
    if func == llocal:
        prefix = ''
        kwargs = {}
    else:
        prefix = 'source ~/.bashrc && '
        kwargs = {'pty': False}
    #run command will not actually start the server without setting pty=False, I don't know why.
    func(prefix+'{CSPACE_JEESERVER_HOME}/bin/startup.sh -dservice.identifier={service_identifier}',
         **kwargs)
    pid = get_pid(func)

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

def deploy_services():
    stop_server()
    with cd(services_dir):
        _git_pull()
        _build()
        rrun('ant create_db import')
    start_server()

def print_env():
    output = rrun('env')
    print output

def get_pid(func=rrun):
    "pid of java program using unique identifier"
    pid = func("ps ww -C java | grep {service_identifier} | awk '{{print$1}}'",True)
    puts(green("pid = " + pid))
    return pid

def rm_pid():
    rrun('touch {CSPACE_JEESERVER_HOME}/bin/tomcat.pid')
    rrun('rm {CSPACE_JEESERVER_HOME}/bin/tomcat.pid')

def cat_log():
    "see tail of catalina.out"
    rrun("tail {CSPACE_JEESERVER_HOME}/logs/catalina.out",)

def _build():
    rrun('ant undeploy deploy')

def _git_pull():
    rrun('git pull origin custom')
        
def local_restart_server():
    llocal('{CSPACE_JEESERVER_HOME}/bin/shutdown.sh')
    llocal('kill -9 `cat {CATALINA_PID}`')
    time.sleep(3)
    llocal('{CSPACE_JEESERVER_HOME}/bin/startup.sh')


##################
# local utils
###################

def _login(func):
    "decorator which uses a session cookie"
    def logged_in(*args,**kwargs):
        _get_cookie()
        func(*args,**kwargs)
        llocal('rm ' + env.cookie_file)
    return logged_in

@hosts('localhost')
def local_tenant_init():
    "shortcut of tenant_init for localhost"
    tenant_init()

@hosts('localhost')
def local_auth_init():
    "shortcut of auth_init for localhost"
    auth_init()

@hosts('localhost')
def local_start_server():
    "shortcut of start_server for localhost"
    start_server(llocal)

wget = " wget --keep-session-cookies --load-cookies {cookie_file} "
tenant = " http://{host_string}:{http_port}/collectionspace/tenant/{tenant}"
# server doesn't prompt for encoding scheme; (basic,digest or NTLM)
# wget_auth = ' --http-user={login_userid} --http-password={password} '

def _get_cookie():
    "login to collectionspace and GET tenant init to reload the configs"
    env.cookie_file = "cookies.txt"
    # env.login_password = prompt("enter password for {}:".format(env.login_userid))
    env.login_password = env['password']
    llocal("""\
          wget -q --keep-session-cookies --save-cookies {cookie_file} \
          --post-data "userid={login_userid}&password={login_password}" \
          http://{host_string}:{http_port}/collectionspace/tenant/{tenant}/login \
          -O /dev/null \
          """)

    cookie = open(env.cookie_file).readlines().pop()
    if "CSPACESESSID" in cookie:
        print(green("logged in successfully"))
    else:
        print(red("not logged in! wrong password?"))
        exit


@_login
def tenant_init():
    "hit tenant/{tenant}/init to reload configs"
    llocal(wget + tenant + '/init' + ' -O-')

@_login
def auth_init():
    "hit authorities/initialise and authorities/vocab/initialize"
    llocal(wget  + tenant + '/authorities/initialise' + ' -O -')
    llocal(wget  + tenant +'/authorities/vocab/initialize' + ' -O - ')#!!lize!!

def test_collection_object(field_name=None):
    "check if a field exists in fieldsReturned"
    objects_list = services_LIST('collectionobjects')
    csid = _find_default_authority_csid(objects_list)
    object_schema_dump = services_LIST('collectionobjects/{csid}'.format(csid=csid))
    if field_name in object_schema_dump:
        print green('yes')
    else: 
        print red('no')

def test_authority(authority,field_name=None):
    "use the ?authorities naming style; so organization for orgauthorities(?!) and person for personauthorities"
    env.field_name = field_name
    env.authority = authority
    find_table = "psql -U catalina nuxeo -c '\d' | grep {authority}s_{tenant}"
    if env.host_string == 'localhost':
        with settings(warn_only= True):
            exists = llocal(find_table)
            if exists.failed:
                print red('table not in db')
                return
    if authority == 'organization':
        env.authorities = 'org' + 'authorities'
    else:
        env.authorities = authority + 'authorities'
    env.authority = authority
    authorities_list = services_LIST(authority)

    csid = _find_default_authority_csid(authorities_list)
    success = _post_item_to_authority(authority,csid)
    if success:
        # llocal('rm {}.xml'.format(authority))
        pass

def services_LIST(service):
    env.service = service
    env.login_password = env['password']
    list_response = llocal('wget --user={login_userid} --password={login_password}\
                              --keep-session-cookies \
                              http://{host_string}:{http_port}/cspace-services/{service}\
                              -O - ', True)
    return list_response

def _find_default_authority_csid(string):
    tree = objectify.fromstring(string)
    items = [(getattr(item,'displayName', '-'),item.csid)  for item in tree.findall('list-item')]
    item = filter(lambda item: 'Test' not in str(item[0]), items)
    if not item:
        print red("did you forget to run auth_init?")
        print red( "csid not found in:\n\n") + BeautifulStoneSoup(string).prettify()
        exit()
    csid = item[0][1]
    return csid

def _compose_post_data(authority):
    try:
        string = open('authority_template.xml').read()
    except:
        string = open('../minibuild/authority_template.xml').read()
    new_file = open(authority + '.xml', "w")
    env.doctype = env.authority
    env.schema_name = env.authority + 's_' + 'common'
    env.displayname = authority.capitalize()
    env.short_display_name = authority #?what
    env.description = 'my authority'
    env.tenant_schema_name = authority + 's_' + env.tenant
    env.content = '<{field_name}>somthing</{field_name}>'.format(**env)

    doc = string.format(**env)
    new_file.write(doc)
    new_file.close()


def _post_item_to_authority(authority,csid):
    "use the name of the xml file in this directory without the .xml"
    _compose_post_data(authority)
    env.csid = csid
    response = llocal("curl -i -u {login_userid}:{login_password} -X POST -H \"Content-Type: application/xml\" \
           http://{host_string}:{http_port}/cspace-services/{authorities}/{csid}/items \
           -T {authority}.xml", True)
    tuples = filter(lambda t: ': ' in t, response.split('\r\n'))
    dd = dict(map(lambda string: tuple(string.split(': ')) , tuples))
    if 'Location' not in dd:
        puts(red('Create Request Failed:\n\n') + response)
        puts(response)
        return False
    else:
        _view_item(dd['Location'])
        return True


def _view_item(location, ):
    env.location = location
    response = llocal("curl -i -u {login_userid}:{login_password} \
           {location} ", True)
    soup = BeautifulStoneSoup(response)
    if env.field_name and env.field_name in str(soup):
        print(green("Found it: "+ str(soup(env.field_name))))
    else:
        print(red("Not Found: "))

