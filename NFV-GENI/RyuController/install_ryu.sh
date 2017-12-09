cd ~

git clone git://github.com/osrg/ryu.git

sudo apt-get update

sudo apt-get install python-pip python-dev -y

sudo apt-get install python-eventlet python-routes python-webob python-paramiko -y

sudo pip install -U pip setuptools

cd ryu

sudo python ./setup.py install

sudo pip install ovs

sudo pip install oslo.config

sudo pip install msgpack-python

sudo pip install eventlet --upgrade

sudo pip install tinyrpc


