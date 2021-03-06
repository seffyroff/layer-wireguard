from charms.reactive import when, when_not, set_flag, endpoint_from_name
from charmhelpers import fetch
from charmhelpers.core import hookenv, host

from libwireguard import WireguardHelper

import socket

wh = WireguardHelper()


@when_not('wireguard.installed')
def install_wireguard():
    hookenv.status_set('maintenance', 'Installing Wireguard')
    fetch.add_source(wh.ppa)
    fetch.apt_update()
    fetch.install('wireguard')
    wh.gen_keys()
    set_flag('wireguard.installed')


@when_not('wireguard.configured')
@when('wireguard.installed')
def configure_wireguard():
    hookenv.status_set('maintenance', 'Generating config')
    wh.write_config()
    host.service('enable', wh.service_name)
    host.service('start', wh.service_name)
    hookenv.open_port(wh.charm_config['listen-port'], protocol='UDP')
    if wh.charm_config['forward-ip']:
        wh.enable_forward()
    hookenv.status_set('active', '')
    set_flag('wireguard.configured')


@when('config.changed')
def update_config():
    host.service('stop', wh.service_name)
    wh.write_config()
    host.service('start', wh.service_name)
    if wh.charm_config.changed('listen-port') and\
       wh.charm_config.previous('listen-port') is not None:
        hookenv.close_port(wh.charm_config.previous('listen-port'), protocol='UDP')
        hookenv.open_port(wh.charm_config['listen-port'], protocol='UDP')
    if wh.charm_config.changed('forward-ip') and\
       wh.charm_config.previous('forward-ip') is not None:
        if wh.charm_config['forward-ip']:
            wh.enable_forward()
        else:
            wh.disable_forward()


@when('reverseproxy.ready')
@when_not('reverseproxy.configured')
def configure_reverseproxy():
    interface = endpoint_from_name('reverseproxy')
    if wh.charm_config['proxy-via-hostname']:
        internal_host = socket.getfqdn()
    else:
        internal_host = hookenv.unit_public_ip()
    config = {
        'mode': 'tcp',
        'external_port': wh.charm_config['listen-port'],
        'internal_host': internal_host,
        'internal_port': wh.charm_config['listen-port'],
    }
    interface.configure(config)
