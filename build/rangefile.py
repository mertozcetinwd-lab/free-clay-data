import io, requests
S = requests.Session()
class RangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url = url; self.pos = 0
        for i in range(6):
            try: self.size = int(S.head(url, timeout=60).headers['Content-Length']); break
            except Exception:
                if i == 5: raise
                import time; time.sleep(2 ** i)
        self.bytes = 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b''
        end = min(self.pos + n, self.size) - 1
        for i in range(5):
            try:
                r = S.get(self.url, headers={'Range': f'bytes={self.pos}-{end}'}, timeout=300); r.raise_for_status(); break
            except Exception as e:
                if i == 4: raise
                import time; time.sleep(2 ** i)
        self.pos += len(r.content); self.bytes += len(r.content)
        return r.content
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)
