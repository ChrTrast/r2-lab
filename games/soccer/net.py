"""Ποδόσφαιρο στο δίκτυο του εργαστηρίου (τοπικό δίκτυο), χωρίς ίντερνετ και χωρίς server, όπως το
SuperTuxKart στο LAN. Δουλεύει το ίδιο σε Windows και Linux.

- Ένας υπολογιστής «φτιάχνει γήπεδο» (Host). Αυτός τρέχει τον αγώνα (logic.Match) και στέλνει στους
  άλλους 30 φορές το δευτερόλεπτο πού είναι τα R2 και η μπάλα.
- Οι άλλοι (Client) στέλνουν μόνο ποια πλήκτρα πατάνε, και ζωγραφίζουν ό,τι τους στέλνει.
- Σε κάθε υπολογιστή μπορούν να παίζουν δύο παιδιά στο ίδιο πληκτρολόγιο (W A S D και βελάκια).
  Κάθε παίκτης έχει "pc": ποιος υπολογιστής τον παίζει (0 = αυτός με το γήπεδο, None = ρομπότ).
- Για να βρεθούν τα γήπεδα χωρίς να γράφει κανείς διευθύνσεις: όποιος ψάχνει (Finder) στέλνει κάθε
  δευτερόλεπτο μια ερώτηση σε όλο το δίκτυο (UDP broadcast, θύρα DISC_PORT) και κάθε γήπεδο απαντά.
  Αν το δίκτυο δεν αφήνει τα broadcast, γράφεις τη διεύθυνση του γηπέδου (φαίνεται στην «Αλλαγή ομάδων»).
- Ο αγώνας: σύνδεση TCP στη θύρα GAME_PORT (ή στις επόμενες, αν είναι πιασμένη), μηνύματα JSON,
  ένα σε κάθε γραμμή. Το τείχος προστασίας χρειάζεται άδεια μόνο στον υπολογιστή με το γήπεδο
  (ο installer των Windows τη δίνει μόνος του).

Όλα είναι «non-blocking»: η οθόνη καλεί poll() σε κάθε καρέ και δεν περιμένει ποτέ το δίκτυο.
"""
import json
import math
import select
import socket
import struct
import sys
import time
import unicodedata
import uuid
from collections import deque

from core import __version__ as VERSION
from . import logic as L

DISC_PORT = 47811
GAME_PORT = 47812
PORT_TRIES = 16
FIND_EVERY = 1.0          # κάθε πότε ρωτάει ο Finder
FORGET_AFTER = 3.5        # γήπεδο που δεν απάντησε τόση ώρα σβήνει από τη λίστα
SNAP_EVERY = 1 / 30       # θέσεις των R2 και της μπάλας
PING_EVERY = 1.0          # στην «Αλλαγή ομάδων», για να ξέρουν όλοι ότι η σύνδεση ζει
INPUT_EVERY = 0.1
CONNECT_TIMEOUT = 4.0
SILENCE = 6.0             # τόση ώρα χωρίς μήνυμα = χάθηκε η σύνδεση
HELLO_TIMEOUT = 5.0
BACKLOG = 32768           # αν ένας υπολογιστής αργεί να διαβάσει, δεν του στέλνουμε κι άλλες θέσεις
DELAY = 0.08              # ο Client δείχνει τον αγώνα λίγο πίσω, για να κινούνται ομαλά τα R2
NAME_MAX = 10
BOT_LEVEL = "normal"
WINDOWS = sys.platform.startswith("win")


# ------------------------------------------------------------- ονόματα
def typed_name(text):
    """Το όνομα όπως το γράφει το παιδί: κεφαλαία χωρίς τόνους, μόνο γράμματα, αριθμοί και κενό."""
    out = []
    for ch in unicodedata.normalize("NFD", text.upper()):
        if unicodedata.category(ch) == "Mn":
            continue
        if ch.isalnum() or ch == " ":
            out.append(ch)
    return "".join(out).lstrip()[:NAME_MAX]


def clean_name(text):
    return " ".join(typed_name(text).split())


def _unique(name, taken):
    if name not in taken:
        return name
    for i in range(2, 99):
        cand = f"{name[:NAME_MAX - 2]} {i}"
        if cand not in taken:
            return cand
    return name


# ------------------------------------------------------------- διευθύνσεις
def local_addresses():
    """[(ip, broadcast)] για κάθε κάρτα δικτύου του υπολογιστή, χωρίς το 127.x."""
    found = {}
    if sys.platform.startswith("linux"):
        try:
            import fcntl
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                for _, name in socket.if_nameindex():
                    if name == "lo":
                        continue
                    req = struct.pack("256s", name.encode()[:15])
                    try:
                        ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, req)[20:24])    # SIOCGIFADDR
                    except OSError:
                        continue
                    try:
                        bc = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8919, req)[20:24])    # SIOCGIFBRDADDR
                    except OSError:
                        bc = None
                    found[ip] = bc
            finally:
                s.close()
        except (ImportError, OSError, AttributeError):
            pass
    first = primary_ip()
    if first:
        found.setdefault(first, None)
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            found.setdefault(ip, None)
    except OSError:
        pass
    out = []
    for ip, bc in found.items():
        if ip.startswith("127.") or ip == "0.0.0.0":
            continue
        if not bc or bc == "0.0.0.0":
            bc = ".".join(ip.split(".")[:3] + ["255"])      # μάντεμα: τα περισσότερα δίκτυα είναι /24
        out.append((ip, bc))
    return out


def primary_ip():
    """Η διεύθυνση του υπολογιστή στο τοπικό δίκτυο (αυτή που δείχνουμε στα παιδιά)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.254.254.254", 1))           # δεν στέλνει τίποτα, μόνο διαλέγει κάρτα δικτύου
        ip = s.getsockname()[0]
        if not ip.startswith("127.") and ip != "0.0.0.0":
            return ip
    except OSError:
        pass
    finally:
        s.close()
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return None


def valid_ip(text):
    parts = text.strip().split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


# ------------------------------------------------------------- σύνδεση με γραμμές JSON
def _encode(msg):
    return (json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


class Conn:
    def __init__(self, sock):
        self.sock = sock
        sock.setblocking(False)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        self.inb = b""
        self.out = b""
        self.closed = False
        self.heard = time.monotonic()
        self.born = self.heard

    def send(self, msg):
        if not self.closed:
            self.out += _encode(msg)
            self.flush()

    def flush(self):
        while self.out and not self.closed:
            try:
                n = self.sock.send(self.out)
            except (BlockingIOError, InterruptedError):
                return
            except OSError:
                self.close()
                return
            if n <= 0:
                return
            self.out = self.out[n:]

    def read(self):
        msgs = []
        while not self.closed:
            try:
                data = self.sock.recv(65536)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                self.close()
                break
            if not data:
                self.close()
                break
            self.heard = time.monotonic()
            self.inb += data
            if len(self.inb) > 1 << 20:
                self.close()
                break
        while b"\n" in self.inb:
            line, self.inb = self.inb.split(b"\n", 1)
            try:
                m = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(m, dict):
                msgs.append(m)
        return msgs

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.sock.close()
            except OSError:
                pass


# ------------------------------------------------------------- αναζήτηση γηπέδων
class Finder:
    """Ψάχνει γήπεδα στο τοπικό δίκτυο. fields(): τα γήπεδα που απάντησαν πρόσφατα."""

    def __init__(self, port=DISC_PORT):
        self.port = port
        self.found = {}
        self.manual = []
        self.socks = []
        self.addrs = local_addresses()
        self._last = -FIND_EVERY
        main = self._socket("")
        if main is not None:
            self.socks.append(main)
        for ip, _ in self.addrs:
            s = self._socket(ip)
            if s is not None:
                self.socks.append(s)

    @staticmethod
    def _socket(ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind((ip, 0))
            s.setblocking(False)
            return s
        except OSError:
            return None

    def add_manual(self, ip):
        ip = ip.strip()
        if valid_ip(ip) and ip not in self.manual:
            self.manual.append(ip)
        self._last = -FIND_EVERY

    def _send(self):
        msg = _encode({"t": "find", "v": VERSION})
        dests = {("255.255.255.255", self.port), ("127.0.0.1", self.port)}
        dests |= {(bc, self.port) for _, bc in self.addrs}
        dests |= {(ip, self.port) for ip in self.manual}
        for i, s in enumerate(self.socks):
            for d in (dests if i == 0 else {("255.255.255.255", self.port)} | {(bc, self.port) for _, bc in self.addrs}):
                try:
                    s.sendto(msg, d)
                except OSError:
                    pass

    def poll(self):
        now = time.monotonic()
        if now - self._last >= FIND_EVERY:
            self._last = now
            self._send()
        for s in self.socks:
            while True:
                try:
                    data, (ip, _) = s.recvfrom(4096)
                except (BlockingIOError, InterruptedError):
                    break
                except OSError:
                    break
                try:
                    m = json.loads(data.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                if not isinstance(m, dict) or m.get("t") != "field" or not m.get("id"):
                    continue
                old = self.found.get(m["id"])
                addr = old["addr"] if old and not old["addr"].startswith("127.") else ip
                self.found[m["id"]] = dict(m, addr=addr, seen=now)
        for key in [k for k, f in self.found.items() if now - f["seen"] > FORGET_AFTER]:
            del self.found[key]

    def fields(self):
        return sorted(self.found.values(), key=lambda f: (f.get("state") != "lobby", f.get("name", ""), f["id"]))

    def close(self):
        for s in self.socks:
            try:
                s.close()
            except OSError:
                pass
        self.socks = []


# ------------------------------------------------------------- ο υπολογιστής με το γήπεδο
class Host:
    role = "host"

    def __init__(self, name, minutes=3, port=GAME_PORT, disc_port=DISC_PORT):
        self.name = clean_name(name) or "ΓΗΠΕΔΟ"
        self.minutes = minutes if minutes in L.MINUTES else 3
        self.id = uuid.uuid4().hex[:10]
        self.me = 1
        self.pc = 0
        self.players = [{"id": 1, "name": self.name, "team": L.BLUE, "bot": None, "host": True, "pc": 0}]
        self._next = 2
        self._next_pc = 1
        self.conns = {}               # pc -> Conn
        self.pending = []
        self.inputs = {}
        self.match = None
        self.match_no = 0
        self.state = "lobby"
        self.ip = primary_ip() or "127.0.0.1"
        self.closed = False
        self._events = []
        self._snap_t = 0.0
        self._ping_t = 0.0
        self._open_server(port)
        self._open_beacon(disc_port)

    # ---------------------------------------------------------- sockets
    def _open_server(self, port):
        last = None
        for p in range(port, port + PORT_TRIES):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                if WINDOWS:
                    s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
                else:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", p))
                s.listen(8)
                s.setblocking(False)
                self.server, self.port = s, p
                return
            except OSError as e:
                last = e
                s.close()
        raise OSError(f"καμία ελεύθερη θύρα ({last})")

    def _open_beacon(self, disc_port):
        self.beacon = None
        try:
            b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            b.bind(("", disc_port))
            b.setblocking(False)
            self.beacon = b
        except OSError:
            self.beacon = None          # χωρίς αυτό, οι άλλοι μπαίνουν μόνο με τη διεύθυνση

    def info(self):
        nb = sum(1 for p in self.players if p["team"] == L.BLUE)
        return {"t": "field", "id": self.id, "name": self.name, "port": self.port, "v": VERSION,
                "state": self.state, "n": [nb, len(self.players) - nb], "max": L.MAX_TEAM,
                "sc": [self.match.score[L.BLUE], self.match.score[L.YELLOW]] if self.match else [0, 0]}

    # ---------------------------------------------------------- παίκτες
    def team_count(self, team):
        return sum(1 for p in self.players if p["team"] == team)

    def player(self, pid):
        return next((p for p in self.players if p["id"] == pid), None)

    def pc_ids(self, pc):
        """Οι παίκτες ενός υπολογιστή, με τη σειρά που μπήκαν (ο πρώτος παίζει με W A S D)."""
        return sorted(p["id"] for p in self.players if p.get("pc") == pc and not p["bot"])

    def mine(self):
        return self.pc_ids(self.pc)

    def _join_team(self):
        nb, ny = self.team_count(L.BLUE), self.team_count(L.YELLOW)
        if nb >= L.MAX_TEAM and ny >= L.MAX_TEAM:
            return None
        if nb >= L.MAX_TEAM:
            return L.YELLOW
        if ny >= L.MAX_TEAM:
            return L.BLUE
        return L.BLUE if nb <= ny else L.YELLOW

    def swap(self, pid):
        p = self.player(pid)
        if p and self.state == "lobby" and self.team_count(L.other(p["team"])) < L.MAX_TEAM:
            p["team"] = L.other(p["team"])
            self._send_lobby()
            return True
        return False

    def add_bot(self, team):
        if self.state != "lobby" or self.team_count(team) >= L.MAX_TEAM:
            return None
        taken = {p["name"] for p in self.players}
        name = "ΡΟΜΠΟΤ" if "ΡΟΜΠΟΤ" not in taken else _unique("ΡΟΜΠΟΤ", taken)
        p = {"id": self._next, "name": name, "team": team, "bot": BOT_LEVEL, "host": False, "pc": None}
        self._next += 1
        self.players.append(p)
        self._send_lobby()
        return p["id"]

    def add_second(self, pc, name):
        """Δεύτερος παίκτης στον ίδιο υπολογιστή (παίζει με τα βελάκια). Επιστρέφει το id ή None."""
        if self.state != "lobby" or len(self.pc_ids(pc)) != 1:
            return None
        team = self._join_team()
        if team is None:
            return None
        name = _unique(clean_name(str(name)) or "ΠΑΙΚΤΗΣ", {p["name"] for p in self.players})
        pid = self._next
        self._next += 1
        self.players.append({"id": pid, "name": name, "team": team, "bot": None, "host": False, "pc": pc})
        self._send_lobby()
        return pid

    def drop_second(self, pc, pid):
        """Ο δεύτερος παίκτης ενός υπολογιστή σταματά να παίζει (ο πρώτος μένει)."""
        ids = self.pc_ids(pc)
        if len(ids) == 2 and pid == ids[1] and self.state == "lobby":
            self.remove(pid)

    def add_local(self, name):
        return self.add_second(self.pc, name)

    def drop_local(self, pid):
        self.drop_second(self.pc, pid)

    def remove(self, pid):
        """Βγάζει έναν παίκτη (ή ρομπότ). Ο ίδιος ο οικοδεσπότης δεν βγαίνει έτσι (close())."""
        p = self.player(pid)
        if pid == self.me or p is None:
            return
        self.players.remove(p)
        self.inputs.pop(pid, None)
        if self.match:
            self.match.remove(pid)
            self._send_all({"t": "left", "id": pid})
        pc = p.get("pc")
        if pc in self.conns and not self.pc_ids(pc):      # ο υπολογιστής δεν έχει πια παίκτη
            self.conns.pop(pc).close()
        self._send_lobby()

    def _drop_pc(self, pc):
        """Ένας υπολογιστής έφυγε από το δίκτυο: βγαίνουν όλοι οι παίκτες του."""
        conn = self.conns.pop(pc, None)
        if conn:
            conn.close()
        for pid in self.pc_ids(pc):
            self.remove(pid)

    def set_minutes(self, m):
        if m in L.MINUTES and self.state == "lobby":
            self.minutes = m
            self._send_lobby()

    def can_start(self):
        return self.state == "lobby" and self.team_count(L.BLUE) > 0 and self.team_count(L.YELLOW) > 0

    def start(self):
        """«Ξεκίνα τον αγώνα!» (και «Ξανά» μετά το τέλος, με τις ίδιες ομάδες)."""
        self.match = L.Match(self.players, self.minutes)
        self.match_no += 1
        self.state = "match"
        self.inputs = {}
        self._events = []
        self._send_all({"t": "start", "roster": self.match.roster(), "min": self.minutes, "no": self.match_no})
        self._send_snapshot()
        return True

    def again(self):
        if self.state in ("match", "end"):
            self.state = "lobby"
            self.start()

    def to_lobby(self):
        """«Αλλαγή ομάδων»: όλοι γυρίζουν στις ομάδες, μπορούν να μπουν και καινούργιοι."""
        self.state = "lobby"
        self.match = None
        self._send_lobby()

    def lobby_msg(self):
        return {"t": "lobby", "players": self.players, "min": self.minutes, "host": self.name, "addr": self.ip}

    def _send_lobby(self):
        if self.state == "lobby":
            self._send_all(self.lobby_msg())

    def _send_all(self, msg):
        data = _encode(msg)
        for c in self.conns.values():
            if not c.closed:
                c.out += data
                c.flush()

    def _send_snapshot(self):
        snap = self.match.snapshot()
        snap["t"] = "s"
        snap["ev"] = self._events
        self._events = []
        data = _encode(snap)
        for c in self.conns.values():
            if not c.closed and len(c.out) < BACKLOG:
                c.out += data
                c.flush()

    # ---------------------------------------------------------- κάθε καρέ
    def poll(self):
        if self.closed:
            return
        now = time.monotonic()
        while True:
            try:
                sock, _ = self.server.accept()
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            self.pending.append(Conn(sock))
        for c in list(self.pending):
            for m in c.read():
                if m.get("t") == "hello":
                    self._hello(c, m)
                    break
            if c.closed or now - c.born > HELLO_TIMEOUT:
                c.close()
            if c.closed or c in self.conns.values():
                self.pending.remove(c)
        for pc, c in list(self.conns.items()):
            for m in c.read():
                self._message(pc, c, m)
            if c.closed:
                self._drop_pc(pc)
        self._answer_finders()
        if self.state != "match" and now - self._ping_t > PING_EVERY:
            self._ping_t = now
            self._send_all({"t": "ping"})

    def _hello(self, c, m):
        if m.get("v") != VERSION:
            c.send({"t": "deny", "why": "version", "v": VERSION})
            c.close()
            return
        if self.state != "lobby":
            c.send({"t": "deny", "why": "playing"})
            c.close()
            return
        team = self._join_team()
        if team is None:
            c.send({"t": "deny", "why": "full"})
            c.close()
            return
        name = _unique(clean_name(str(m.get("name", ""))) or "ΠΑΙΚΤΗΣ", {p["name"] for p in self.players})
        pid, pc = self._next, self._next_pc
        self._next += 1
        self._next_pc += 1
        self.players.append({"id": pid, "name": name, "team": team, "bot": None, "host": False, "pc": pc})
        self.conns[pc] = c
        c.send({"t": "welcome", "you": pid, "pc": pc, "host": self.name})
        self._send_lobby()

    def _message(self, pc, c, m):
        """Ένα μήνυμα από τον υπολογιστή pc. Δέχεται μόνο ό,τι αφορά τους δικούς του παίκτες."""
        t = m.get("t")
        mine = self.pc_ids(pc)
        if t == "in":
            rows = m.get("i")
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, list) and len(row) == 4 and row[0] in mine:
                    self.inputs[row[0]] = L.Input.from_list(row[1:])
        elif t == "swap":
            pid = m.get("id")
            if pid in mine:
                self.swap(pid)
        elif t == "add":
            self.add_second(pc, m.get("name", ""))
        elif t == "drop":
            self.drop_second(pc, m.get("id"))
        elif t == "bye":
            c.close()

    def _answer_finders(self):
        if self.beacon is None:
            return
        while True:
            try:
                data, addr = self.beacon.recvfrom(4096)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            try:
                m = json.loads(data.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(m, dict) and m.get("t") == "find":
                try:
                    self.beacon.sendto(_encode(self.info()), addr)
                except OSError:
                    pass

    def update(self, dt, my_inputs):
        """Τρέχει τον αγώνα. my_inputs: {id: Input} για τους παίκτες αυτού του υπολογιστή
        (ή ένα Input για τον πρώτο). Επιστρέφει τα γεγονότα (για τους ήχους εδώ)."""
        self.poll()
        if self.state not in ("match", "end") or self.match is None:
            return []
        if isinstance(my_inputs, L.Input):
            my_inputs = {self.me: my_inputs}
        inputs = dict(self.inputs)
        mine = self.mine()
        inputs.update({pid: inp for pid, inp in my_inputs.items() if pid in mine})
        events = self.match.update(dt, inputs)
        self._events += events
        if self.match.phase == "end":
            self.state = "end"
        self._snap_t += dt
        if self._snap_t >= SNAP_EVERY:
            self._snap_t = 0.0
            self._send_snapshot()
        return events

    def view(self, now=None):
        return self.match.snapshot() if self.match else None

    def roster(self):
        return {p["id"]: p for p in (self.match.roster() if self.match else self.players)}

    def humans(self):
        return sum(1 for p in self.players if not p["bot"])

    def close(self):
        if self.closed:
            return
        self._send_all({"t": "bye"})
        for c in list(self.conns.values()) + self.pending:
            c.flush()
            c.close()
        self.conns, self.pending = {}, []
        for s in (self.server, self.beacon):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        self.closed = True


# ------------------------------------------------------------- όποιος μπαίνει σε γήπεδο
class Client:
    role = "client"

    def __init__(self, name, addr, port):
        self.name = clean_name(name) or "ΠΑΙΚΤΗΣ"
        self.addr, self.port = addr, port
        self.state = "connecting"      # connecting, hello, lobby, match, closed
        self.error = None
        self.me = None
        self.pc = None
        self.players = []
        self.minutes = 3
        self.host_name = ""
        self.host_ip = addr
        self.roster_list = []
        self.match_no = 0
        self.snaps = deque(maxlen=16)
        self.offset = None
        self._events = []
        self._inp = None
        self._inp_t = 0.0
        self.conn = None
        self._t0 = time.monotonic()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        try:
            self.sock.connect_ex((addr, port))
        except OSError as e:
            self._fail("Δεν βρέθηκε το γήπεδο.", e)

    def _fail(self, text, err=None):
        self.state = "closed"
        if self.error is None:
            self.error = text
        if self.conn:
            self.conn.close()
        else:
            try:
                self.sock.close()
            except OSError:
                pass

    def poll(self):
        if self.state == "closed":
            return
        now = time.monotonic()
        if self.state == "connecting":
            try:
                _, w, x = select.select([], [self.sock], [self.sock], 0)
            except (OSError, ValueError):
                self._fail("Δεν βρέθηκε το γήπεδο.")
                return
            if w or x:
                err = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if err or x:
                    self._fail("Δεν βρέθηκε το γήπεδο.")
                    return
                self.conn = Conn(self.sock)
                self.conn.send({"t": "hello", "v": VERSION, "name": self.name})
                self.state = "hello"
            elif now - self._t0 > CONNECT_TIMEOUT:
                self._fail("Δεν βρέθηκε το γήπεδο.")
            return
        for m in self.conn.read():
            self._handle(m, now)
        if self.state == "closed":
            return
        if self.conn.closed:
            self._fail("Το γήπεδο έκλεισε.")
        elif now - self.conn.heard > SILENCE:
            self._fail("Χάθηκε η σύνδεση με το γήπεδο.")

    def _handle(self, m, now):
        t = m.get("t")
        if t == "welcome":
            self.me = m.get("you")
            self.pc = m.get("pc")
            self.host_name = m.get("host", "")
            self.state = "lobby"
        elif t == "deny":
            why = m.get("why")
            if why == "version":
                text = (f"Το γήπεδο έχει άλλη έκδοση του προγράμματος ({m.get('v')}, εδώ {VERSION}). "
                        "Βάλτε την ίδια έκδοση σε όλους τους υπολογιστές.")
            elif why == "full":
                text = "Το γήπεδο είναι γεμάτο."
            else:
                text = "Παίζουν τώρα. Μπες όταν τελειώσει ο αγώνας."
            self._fail(text)
        elif t == "lobby":
            self.players = m.get("players", [])
            self.minutes = m.get("min", 3)
            self.host_name = m.get("host", self.host_name)
            self.host_ip = m.get("addr", self.host_ip)
            if self.state in ("hello", "match", "lobby"):
                self.state = "lobby"
        elif t == "start":
            self.roster_list = m.get("roster", [])
            self.minutes = m.get("min", self.minutes)
            self.match_no += 1
            self.snaps.clear()
            self.offset = None
            self.state = "match"
        elif t == "s" and self.state == "match":
            sample = now - float(m.get("ht", 0))
            if self.offset is None or sample < self.offset:
                self.offset = sample
            else:
                self.offset += 0.0005
            m["_at"] = now
            self.snaps.append(m)
            self._events += m.get("ev", [])
        elif t == "left":
            self.roster_list = [p for p in self.roster_list if p.get("id") != m.get("id")]
        elif t == "bye":
            self._fail("Το γήπεδο έκλεισε.")

    # ---------------------------------------------------------- ίδια με τον Host, για την οθόνη
    def update(self, dt, my_inputs):
        """my_inputs: {id: Input} για τους παίκτες αυτού του υπολογιστή (ή ένα Input για τον πρώτο)."""
        self.poll()
        if self.state == "match" and self.conn and not self.conn.closed:
            if isinstance(my_inputs, L.Input):
                my_inputs = {self.me: my_inputs}
            rows = [[pid] + inp.as_list() for pid, inp in sorted(my_inputs.items()) if pid is not None]
            now = time.monotonic()
            if rows and (rows != self._inp or now - self._inp_t > INPUT_EVERY):
                self._inp, self._inp_t = rows, now
                self.conn.send({"t": "in", "i": rows})
        ev, self._events = self._events, []
        return ev

    def _send(self, msg):
        if self.conn and not self.conn.closed:
            self.conn.send(msg)

    def mine(self):
        """Οι παίκτες αυτού του υπολογιστή, με τη σειρά που μπήκαν (ο πρώτος παίζει με W A S D)."""
        ids = sorted(p["id"] for p in self.players if self.pc is not None and p.get("pc") == self.pc
                     and not p.get("bot"))
        return ids or ([self.me] if self.me is not None else [])

    def swap(self, pid=None):
        self._send({"t": "swap", "id": self.me if pid is None else pid})

    def add_local(self, name):
        self._send({"t": "add", "name": name})

    def drop_local(self, pid):
        self._send({"t": "drop", "id": pid})

    def roster(self):
        return {p["id"]: p for p in self.roster_list}

    def humans(self):
        return sum(1 for p in self.roster_list if not p.get("bot"))

    def view(self, now=None):
        """Ο αγώνας όπως ήταν πριν από λίγο (DELAY), ανάμεσα σε δύο μηνύματα, για ομαλή κίνηση."""
        if not self.snaps:
            return None
        now = time.monotonic() if now is None else now
        target = now - (self.offset or 0.0) - DELAY
        snaps = self.snaps
        if target <= snaps[0]["ht"]:
            return snaps[0]
        if target >= snaps[-1]["ht"]:
            return snaps[-1]
        for i in range(len(snaps) - 1, 0, -1):
            s0, s1 = snaps[i - 1], snaps[i]
            if s0["ht"] <= target <= s1["ht"]:
                span = s1["ht"] - s0["ht"]
                k = (target - s0["ht"]) / span if span > 0 else 1.0
                return _blend(s0, s1, k)
        return snaps[-1]

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.send({"t": "bye"})
            self.conn.flush()
            self.conn.close()
        elif self.conn is None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.state = "closed"


def _blend(s0, s1, k):
    out = dict(s0 if k < 0.5 else s1)
    jump = 150.0

    def mix(a, b):
        return a + (b - a) * k

    bx0, by0 = s0["ball"]
    bx1, by1 = s1["ball"]
    if math.hypot(bx1 - bx0, by1 - by0) < jump:
        out["ball"] = [mix(bx0, bx1), mix(by0, by1)]
    old = {r[0]: r for r in s0["r"]}
    robots = []
    for r in s1["r"]:
        o = old.get(r[0])
        if o is None or math.hypot(r[1] - o[1], r[2] - o[2]) > jump:
            robots.append(r if k >= 0.5 else (o or r))
            continue
        a = o[3] + L.wrap(r[3] - o[3]) * k
        robots.append([r[0], mix(o[1], r[1]), mix(o[2], r[2]), a] + list(r[4:]))
    out["r"] = robots
    return out
