import ncs
from ncs.application import Service

TEMPLATES = ('l3vpn-vrf', 'l3vpn-qos', 'l3vpn-interface', 'l3vpn-bgp')


class ServiceCallbacks(Service):

    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

        rate_bps = service.bandwidth * 1000

        # Cisco's usual policer sizing: burst = 1.5 s of traffic, peak = 2x.
        # 1676 kbps -> 1676000 * 1.5 / 8 = 314250 bytes, peak 628500.
        burst = service.qos.burst if service.qos.burst is not None else rate_bps * 3 // 16
        peak = service.qos.peak_burst if service.qos.peak_burst is not None else burst * 2

        tvars = ncs.template.Variables()
        tvars.add('BGP_AS', str(service.bgp_as))
        tvars.add('IPV6_ENABLE', 'true' if service.ipv6_enable else 'false')
        tvars.add('INTF_ID', f'{service.interface.interface_id}.{service.interface.subintf_id}')
        tvars.add('POLICE_RATE_BPS', str(rate_bps))
        tvars.add('SHAPE_RATE_BPS', str(rate_bps))
        tvars.add('BURST_BYTES', str(burst))
        tvars.add('PEAK_BURST_BYTES', str(peak))

        template = ncs.template.Template(service)
        for name in TEMPLATES:
            template.apply(name, tvars)


class Main(ncs.application.Application):
    def setup(self):
        self.log.info('Main RUNNING')
        self.register_service('l3vpn-service-servicepoint', ServiceCallbacks)

    def teardown(self):
        self.log.info('Main FINISHED')