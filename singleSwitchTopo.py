from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNetConnections, dumpNodeConnections
from mininet.log import setLogLevel


class SingleSwitchTopo(Topo):
    "Single swich connected to host"
    def build(self, n=2):
            switch = self.addSwitch('s1')
            # Python's range(N) generates 0..N-1
            for h in range(n):
                host = self.addHost('h%s' %(h+1))
                self.addLink(host,switch)
def simpleTest():
        "Create and test a Simple network"
        topo = SingleSwitchTopo(n=4)
        net = Mininet(topo)
        net.start()
        print("Dumping host conenctions")
        dumpNodeConnections(net.hosts)
        print("Testig network connnectivity")
        net.pingAll()
        net.stop()

if __name__ =='__main__':
        #Tell mininet to print usefull information
        setLogLevel('info')
        simpleTest()
