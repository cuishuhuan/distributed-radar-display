import json
import gzip
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bridge import MessageStore, make_handler
from simulation import FleetSimulator


class SimulationTests(unittest.TestCase):
    def test_clock_rate_and_history(self):
        now = [1000.0]
        fleet = FleetSimulator(clock=lambda: now[0])
        initial = fleet.snapshot()
        self.assertEqual(len({s['id'] for s in initial['tracks']}), 24)
        now[0] += 10
        advanced = fleet.snapshot()
        self.assertNotEqual(initial['tracks'][0]['lat'], advanced['tracks'][0]['lat'])
        fleet.set_rate(20)
        self.assertEqual(advanced['tracks'][0]['lat'], fleet.snapshot()['tracks'][0]['lat'])
        self.assertEqual(fleet.snapshot()['simulationRate'], 20)
        now[0] += 10000
        self.assertEqual(len(fleet.snapshot()['tracks'][0]['history']), 180)
        for value in [0, 21, True, 1.5, None, float('nan')]:
            with self.assertRaises(ValueError):
                fleet.set_rate(value)
        self.assertEqual(MessageStore().snapshot()['tracks'], [])

    def test_http_shared_state(self):
        store = MessageStore(FleetSimulator())
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(store, None))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:%d' % server.server_port
        try:
            def request(path, data=None):
                req = Request(base+path, data=json.dumps(data).encode() if data is not None else None, headers={'Content-Type': 'application/json'})
                with urlopen(req) as response:
                    return json.load(response)
            self.assertEqual(len(request('/api/state')['tracks']), 24)
            with urlopen(Request(base+'/api/state', headers={'Accept-Encoding': 'gzip'})) as response:
                self.assertEqual(response.headers['Content-Encoding'], 'gzip')
                self.assertEqual(len(json.loads(gzip.decompress(response.read()))['tracks']), 24)
            request('/api/simulation/rate', {'rate': 12})
            self.assertEqual(request('/api/state')['simulationRate'], 12)
            with self.assertRaises(HTTPError) as error:
                request('/api/simulation/rate', {'rate': 99})
            self.assertEqual(error.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
