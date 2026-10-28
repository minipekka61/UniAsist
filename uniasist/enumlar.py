from enum import Enum


class Rol(Enum):
    OGRENCI = "OGRENCI"
    YONETICI = "YONETICI"


class HesapDurumu(Enum):
    AKTIF = "AKTIF"
    DEVRE_DISI = "DEVRE_DISI"


class KaynakDurumu(Enum):
    AKTIF = "AKTIF"
    PASIF = "PASIF"


class KayitDurumu(Enum):
    ACIK = "ACIK"
    COZULDU = "COZULDU"


class GeriBildirimTuru(Enum):
    YARARLI = "YARARLI"
    YARARSIZ = "YARARSIZ"


class GonderenTuru(Enum):
    KULLANICI = "KULLANICI"
    SISTEM = "SISTEM"


class SonucDurumu(Enum):
    YANIT = "YANIT"
    ICERIK_BULUNAMADI = "ICERIK_BULUNAMADI"
    SERVIS_HATASI = "SERVIS_HATASI"
