import os

from fabric.api import *

if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
    env.use_ssh_config = True

def dev():
    env.hosts           = ['root@onedollar.projects.nng.bz',]
    env.project_data    = {'project': 'onedollar'}
    env.remote_code_dir = '/webapps/%(project)s_backend/' % env.project_data

def prod():
    env.hosts           = ['root@api.onedollarapp.biz',]
    env.project_data    = {'project': 'onedollar'}
    env.remote_code_dir = '/webapps/%(project)s_backend/' % env.project_data

def commit():
    local("git add -p && git commit")

def push():
    local("git push")

def prepare_deploy():
    commit()
    push()

def deploy():
    require('hosts', provided_by=[dev])
    require('remote_code_dir', provided_by=[dev])
    require('project_data', provided_by=[dev])

    run("test -d %s" % env.remote_code_dir)
    with cd(env.remote_code_dir), prefix(". /usr/local/bin/virtualenvwrapper.sh; workon %(project)s_backend" % env.project_data):
        run("git pull origin master")
        run("git submodule update")
        run("pip install -r requirements.txt")
        run("./manage.py migrate")
        run("./manage.py collectstatic --noinput")
        sudo("supervisorctl restart onedollar")
