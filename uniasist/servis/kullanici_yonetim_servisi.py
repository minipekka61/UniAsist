from uniasist.enumlar import Rol
from uniasist.hatalar import IsKuraliIhlaliException


class KullaniciYonetimServisi:
    def __init__(self, kullanici_deposu, kimlik_dogrulama_servisi):
        self.kullanici_deposu = kullanici_deposu
        self.kimlik_dogrulama_servisi = kimlik_dogrulama_servisi

    def kullanicilariListele(self, arama=""):
        return self.kullanici_deposu.ara(arama or "")

    def rolDegistir(self, yonetici_id, hedef_id, yeni_rol):
        if yonetici_id == hedef_id:
            raise IsKuraliIhlaliException(
                "IK-10", "Yönetici kendi rolünü değiştiremez."
            )
        hedef = self.kullanici_deposu.idIleBul(hedef_id)
        if hedef is None:
            raise IsKuraliIhlaliException("IK-10", "Kullanıcı bulunamadı.")
        if hedef.rol == Rol.YONETICI:
            raise IsKuraliIhlaliException(
                "IK-10", "Yönetici rolündeki kullanıcının rolü değiştirilemez."
            )
        if yeni_rol not in (Rol.OGRENCI, Rol.PERSONEL):
            raise IsKuraliIhlaliException(
                "IK-32", "Bu sürümde yalnızca Öğrenci ve Personel rolleri arasında geçiş yapılabilir."
            )
        hedef.rolDegistir(yeni_rol)
        self.kullanici_deposu.kaydet(hedef)

    def hesapDevreDisiBirak(self, yonetici_id, hedef_id):
        if yonetici_id == hedef_id:
            raise IsKuraliIhlaliException(
                "IK-10", "Yönetici kendi hesabını devre dışı bırakamaz."
            )
        hedef = self.kullanici_deposu.idIleBul(hedef_id)
        if hedef is None:
            raise IsKuraliIhlaliException("IK-10", "Kullanıcı bulunamadı.")
        if hedef.rol == Rol.YONETICI and self.kullanici_deposu.aktifYoneticiSayisi() <= 1:
            raise IsKuraliIhlaliException(
                "IK-10", "Sistemde en az bir aktif yönetici hesabı bulunmalıdır."
            )
        hedef.devreDisiBirak()
        self.kullanici_deposu.kaydet(hedef)
        self.kimlik_dogrulama_servisi.kullaniciOturumlariniSonlandir(hedef_id)
