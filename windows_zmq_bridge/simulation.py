"""Shared server-clock fleet simulation; no browser is needed to advance ships."""
import math
import threading
import time
from collections import deque
from datetime import datetime, timezone


def destination(origin, distance, bearing):
    lat, lon, angle = map(math.radians, (origin['lat'], origin['lon'], bearing))
    arc = distance / 6371
    end = math.asin(math.sin(lat) * math.cos(arc) + math.cos(lat) * math.sin(arc) * math.cos(angle))
    return {'lat': math.degrees(end), 'lon': math.degrees(lon + math.atan2(math.sin(angle) * math.sin(arc) * math.cos(lat), math.cos(arc) - math.sin(lat) * math.sin(end)))}


def distance(a, b):
    return math.hypot((b['lon'] - a['lon']) * 111.32 * math.cos(math.radians((a['lat'] + b['lat']) / 2)), (b['lat'] - a['lat']) * 110.57)


def bearing(a, b):
    return math.degrees(math.atan2((b['lon'] - a['lon']) * math.cos(math.radians((a['lat'] + b['lat']) / 2)), b['lat'] - a['lat'])) % 360


class FleetSimulator:
    def __init__(self, rate=5, clock=time.monotonic):
        self.clock = clock
        self.anchor = clock()
        self.wall_offset = time.time() - self.anchor
        self.elapsed = 0
        self.rate = self.validate_rate(rate)
        self.lock = threading.RLock()
        names = '南沙海运01 珠江货轮02 粤港滚装03 海巡04 南沙集装箱05 珠江客船06 外海货轮07 南沙油轮08 华南散货09 海港集装箱10 珠江货轮11 外海客船12 湾区集运13 远洋散货14 粤海客轮15 海事巡逻16 珠港拖轮17 南洋油轮18 外锚散货19 岭南集装箱20 湾区滚装21 远海科考22 珠江散货23 南沙邮轮24'.split()
        speeds = [18,14,22,10,16,8,24,12,20,15,9,17,13,19,11,21,16,12,10,23,15,9,18,14]
        photos = ['optical.jpg'] + ['ship%02d.jpg' % i for i in range(2, 12)] + ['three-d.jpg']
        self.ships = []
        for i, name in enumerate(names):
            lane, band = i % 6, i // 6
            heading, inner, outer = 160 + lane * 3.5, 24 + band * 1.2, 34 + band * 1.3
            origin = {'lon': 113.613836, 'lat': 22.766758}
            route = [destination(origin, d, a) for d, a in [(inner, heading-.55), (outer, heading-.55), (outer, heading+.55), (inner, heading+.55)]]
            if i % 2:
                route.reverse()
            lengths = [distance(p, route[(j+1) % 4]) for j, p in enumerate(route)]
            ship = {'id': 'SIM-%02d' % (i+1), 'name': name, 'mmsi': str(413690100+i), 'speed': speeds[i], 'threat': 5-i if i < 5 else 0, 'photo': photos[i % len(photos)], 'aisOk': i not in (3,15), 'radarOk': i not in (4,18)}
            self.ships.append((ship, route, lengths, sum(lengths)*i/24))
        self.histories = [deque(maxlen=180) for _ in self.ships]
        self.last_sample = self.anchor - 92
        self._record(self.anchor)

    @staticmethod
    def validate_rate(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= 20 or int(value) != value:
            raise ValueError('仿真倍速必须为 1 至 20 的整数')
        return int(value)

    def _elapsed_at(self, now):
        return self.elapsed + (now - self.anchor) * self.rate

    def _position(self, vessel, elapsed):
        ship, route, lengths, offset = vessel
        remaining = (elapsed * ship['speed'] * 1.852 / 3600 + offset) % sum(lengths)
        for i, length in enumerate(lengths):
            if remaining <= length:
                heading = bearing(route[i], route[(i+1) % 4])
                # Interpolate endpoints so every segment joins exactly without a position jump.
                fraction = remaining / length
                return {'lon': route[i]['lon'] + (route[(i+1)%4]['lon']-route[i]['lon'])*fraction, 'lat': route[i]['lat'] + (route[(i+1)%4]['lat']-route[i]['lat'])*fraction, 'course': heading}
            remaining -= length

    def _record(self, now):
        sample = max(self.last_sample + 1, now - 179)
        while sample <= now:
            for vessel, history in zip(self.ships, self.histories):
                history.append({**self._position(vessel, self._elapsed_at(sample)), 'time': round((sample+self.wall_offset)*1000)})
            self.last_sample = sample
            sample += 1

    def set_rate(self, value):
        value = self.validate_rate(value)
        with self.lock:
            now = self.clock()
            self._record(now)
            self.elapsed = self._elapsed_at(now)
            self.anchor, self.rate = now, value

    def snapshot(self):
        with self.lock:
            now = self.clock()
            self._record(now)
            return {'mode': 'simulation', 'dataSource': 'backend-simulation', 'simulationRate': self.rate, 'updatedUtc': datetime.now(timezone.utc).isoformat(), 'tracks': [{**vessel[0], **self._position(vessel, self._elapsed_at(now)), 'history': list(history)} for vessel, history in zip(self.ships, self.histories)]}
