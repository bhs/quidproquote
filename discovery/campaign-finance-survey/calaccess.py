"""California Secretary of State committee records (CAL-ACCESS), read without a full download.

The state publishes its whole campaign-finance database as one 1.6 GB zip
(https://campaignfinance.cdn.sos.ca.gov/dbwebexport.zip). Only one table is
needed here (FILERNAME_CD.TSV, about 17 MB compressed), so the zip's directory
and that one member are read with HTTP range requests.
"""

import csv
import io
import time
import urllib.error
import urllib.request
import zipfile

URL = "https://campaignfinance.cdn.sos.ca.gov/dbwebexport.zip"
FILERNAME = "CalAccess/DATA/FILERNAME_CD.TSV"


class CalAccessError(RuntimeError):
    pass


class HttpRange(io.RawIOBase):
    """Read-only, seekable view of a remote file fetched by byte ranges."""

    def __init__(self, url):
        self.url = url
        self.pos = 0
        head = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "campaign-finance-survey"})
        with urllib.request.urlopen(head, timeout=60) as resp:
            self.size = int(resp.headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        else:
            self.pos = self.size + offset
        return self.pos

    def read(self, n=-1):
        if n < 0 or self.pos + n > self.size:
            n = self.size - self.pos
        if n <= 0:
            return b""
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(self.url, headers={
                    "Range": "bytes=%d-%d" % (self.pos, self.pos + n - 1),
                    "User-Agent": "campaign-finance-survey"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = resp.read()
                self.pos += len(data)
                return data
            except (urllib.error.URLError, TimeoutError) as exc:
                last = exc
                time.sleep(2 * (attempt + 1))
        raise CalAccessError("range read of %s failed: %s" % (self.url, last))

    def readinto(self, buf):
        data = self.read(len(buf))
        buf[:len(data)] = data
        return len(data)


def parse_filer_names(lines):
    """Index FILERNAME_CD rows (tab separated, with header).

    Returns (by_id, by_xref): by_id maps FILER_ID to the row with the latest
    EFFECT_DT as {"type", "status", "name"}; by_xref maps a legacy XREF_FILER_ID
    to the FILER_ID it belongs to.
    """
    by_id, by_xref, stamp = {}, {}, {}
    reader = csv.DictReader(lines, delimiter="\t", quoting=csv.QUOTE_NONE)
    for row in reader:
        fid = (row.get("FILER_ID") or "").strip()
        if not fid:
            continue
        eff = (row.get("EFFECT_DT") or "").split(" ")[0]
        try:
            month, day, year = (int(x) for x in eff.split("/"))
            key = (year, month, day)
        except ValueError:
            key = (0, 0, 0)
        if fid not in by_id or key >= stamp[fid]:
            stamp[fid] = key
            name = ((row.get("NAML") or "") + " " + (row.get("NAMF") or "")).strip()
            by_id[fid] = {"type": row.get("FILER_TYPE") or "", "status": row.get("STATUS") or "", "name": name}
        xref = (row.get("XREF_FILER_ID") or "").strip()
        if xref and xref != fid:
            by_xref.setdefault(xref, fid)
    return by_id, by_xref


def filer_names():
    """Download and index the state's filer name table (about 350,000 filers)."""
    try:
        archive = zipfile.ZipFile(io.BufferedReader(HttpRange(URL), buffer_size=1 << 16))
        with archive.open(FILERNAME) as member:
            return parse_filer_names(io.TextIOWrapper(member, encoding="latin-1", newline=""))
    except (urllib.error.URLError, zipfile.BadZipFile, KeyError, OSError) as exc:
        raise CalAccessError("CAL-ACCESS filer table unavailable: %s" % exc)
