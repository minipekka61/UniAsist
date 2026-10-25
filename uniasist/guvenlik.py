import hashlib
import hmac
import secrets

_YONTEM = "pbkdf2_sha256"
_ITERASYON = 200000


def sifre_hashle(sifre):
    tuz = secrets.token_hex(16)
    hash_hex = hashlib.pbkdf2_hmac(
        "sha256", sifre.encode("utf-8"), bytes.fromhex(tuz), _ITERASYON
    ).hex()
    return f"{_YONTEM}${_ITERASYON}${tuz}${hash_hex}"


def sifre_dogrula(sifre, saklanan):
    if not isinstance(saklanan, str):
        return False
    parcalar = saklanan.split("$")
    if len(parcalar) != 4 or parcalar[0] != _YONTEM:
        return False
    try:
        iterasyon = int(parcalar[1])
        tuz = bytes.fromhex(parcalar[2])
        beklenen = bytes.fromhex(parcalar[3])
    except ValueError:
        return False
    hesap = hashlib.pbkdf2_hmac(
        "sha256", sifre.encode("utf-8"), tuz, iterasyon
    )
    return hmac.compare_digest(hesap, beklenen)
