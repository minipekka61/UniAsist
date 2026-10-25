from abc import ABC, abstractmethod
from typing import Iterator


class IYapayZekaServisi(ABC):
    @property
    @abstractmethod
    def saglayici_etiketi(self):
        ...

    @abstractmethod
    def yanitUret(self, soru_metni, parcalar, baglam):
        ...

    @abstractmethod
    def gommeUret(self, metin):
        ...

    def yanitUretAkis(self, soru_metni, parcalar, baglam) -> Iterator[str]:
        yield self.yanitUret(soru_metni, parcalar, baglam)
