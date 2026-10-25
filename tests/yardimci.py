from uniasist.depo.veritabani import sema_olustur
import sqlite3


def gecici_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    sema_olustur(conn)
    return conn
