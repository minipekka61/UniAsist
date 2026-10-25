import sys

from uniasist.uygulama import uygulama_olustur

uygulama = uygulama_olustur()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        from uniasist import seed
        from uniasist.kurulum import kur

        seed.kos(kur(seed_yap=False))
        print("Örnek veri yüklendi.")
    else:
        uygulama.run(debug=True, port=5000)
