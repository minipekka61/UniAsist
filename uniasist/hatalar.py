class IsKuraliIhlaliException(Exception):
    def __init__(self, kural_no, mesaj):
        super().__init__(mesaj)
        self.kural_no = kural_no
        self.mesaj = mesaj

    def kural_no_getir(self):
        return self.kural_no
