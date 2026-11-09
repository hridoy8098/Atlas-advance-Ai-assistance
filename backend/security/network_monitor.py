# backend/security/network_monitor.py — live network connection summary

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


class NetworkMonitor:
    def summary(self):
        if psutil is None:
            return {"established": 0, "listening": 0, "total": 0, "top_processes": [],
                    "error": "psutil not installed"}

        established = listening = total = 0
        pid_names = {}
        counts = {}
        try:
            connections = psutil.net_connections(kind="inet")
        except Exception as e:
            return {"established": 0, "listening": 0, "total": 0, "top_processes": [], "error": str(e)}

        for conn in connections:
            total += 1
            if conn.status == psutil.CONN_ESTABLISHED:
                established += 1
            elif conn.status == psutil.CONN_LISTEN:
                listening += 1
            if conn.pid:
                if conn.pid not in pid_names:
                    try:
                        pid_names[conn.pid] = psutil.Process(conn.pid).name()
                    except Exception:
                        pid_names[conn.pid] = f"pid {conn.pid}"
                name = pid_names[conn.pid]
                counts[name] = counts.get(name, 0) + 1

        top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        return {
            "established": established,
            "listening": listening,
            "total": total,
            "top_processes": [{"name": name, "connections": count} for name, count in top],
        }

    def active_connections(self, limit: int = 25):
        if psutil is None:
            return []
        out = []
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status != psutil.CONN_ESTABLISHED:
                    continue
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
                out.append({"local": laddr, "remote": raddr, "pid": conn.pid})
                if len(out) >= limit:
                    break
        except Exception:
            return []
        return out


network_monitor = NetworkMonitor()
