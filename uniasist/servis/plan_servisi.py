import config
from uniasist.enumlar import Plan, Rol
from uniasist.hatalar import IsKuraliIhlaliException


class PlanServisi:
    def __init__(self, kullanici_deposu, soru_kaydi_deposu, bilgi_kaynagi_deposu):
        self.kullanici_deposu = kullanici_deposu
        self.soru_kaydi_deposu = soru_kaydi_deposu
        self.bilgi_kaynagi_deposu = bilgi_kaynagi_deposu

    def haklar(self, kullanici):
        belge_sayisi = len(
            self.bilgi_kaynagi_deposu.sahibinBelgeleri(kullanici.kullanici_id)
        )
        bugunku_soru = self.soru_kaydi_deposu.gunlukSoruSayisi(
            kullanici.kullanici_id
        )
        if kullanici.proMu():
            return {
                "plan": kullanici.plan,
                "belge_sayisi": belge_sayisi,
                "belge_limiti": None,
                "bugunku_soru": bugunku_soru,
                "gunluk_limit": None,
            }
        return {
            "plan": kullanici.plan,
            "belge_sayisi": belge_sayisi,
            "belge_limiti": config.UCRETSIZ_AZAMI_BELGE,
            "bugunku_soru": bugunku_soru,
            "gunluk_limit": config.UCRETSIZ_GUNLUK_SORU,
        }

    def soruHakkiVarMi(self, kullanici):
        if kullanici.proMu():
            return True
        return self.soru_kaydi_deposu.gunlukSoruSayisi(
            kullanici.kullanici_id
        ) < config.UCRETSIZ_GUNLUK_SORU

    def belgeHakkiVarMi(self, kullanici):
        if kullanici.proMu():
            return True
        return len(
            self.bilgi_kaynagi_deposu.sahibinBelgeleri(kullanici.kullanici_id)
        ) < config.UCRETSIZ_AZAMI_BELGE

    def proYap(self, kullanici):
        if kullanici.rol == Rol.YONETICI:
            raise IsKuraliIhlaliException(
                "IK-10", "Yönetici hesapları plan değiştiremez."
            )
        kullanici.plan = Plan.PRO
        self.kullanici_deposu.kaydet(kullanici)
        return kullanici

    def ucretsizeDon(self, kullanici):
        if kullanici.rol == Rol.YONETICI:
            raise IsKuraliIhlaliException(
                "IK-10", "Yönetici hesapları plan değiştiremez."
            )
        kullanici.plan = Plan.UCRETSIZ
        self.kullanici_deposu.kaydet(kullanici)
        return kullanici
