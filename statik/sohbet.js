(function () {
    "use strict";
    var mesajlarKutu = document.getElementById("mesajlar");
    var yaziyor = document.getElementById("yaziyor");
    var form = document.getElementById("soru-formu");
    var soruKutusu = document.getElementById("soru");
    var yeniSohbetDugmesi = document.getElementById("yeni-sohbet");
    var aktifSohbetId = null;
    var girisli = window.uniasistGirisli === true;

    function balonEkle(gonderen, metin) {
        var mesaj = document.createElement("div");
        mesaj.className = "mesaj " + (gonderen === "KULLANICI" ? "mesaj-kullanici" : "mesaj-sistem");
        var balon = document.createElement("div");
        balon.className = "balon";
        var metinEl = document.createElement("div");
        metinEl.className = "metin";
        metinEl.textContent = metin;
        balon.appendChild(metinEl);
        mesaj.appendChild(balon);
        mesajlarKutu.appendChild(mesaj);
        mesajlarKutu.scrollTop = mesajlarKutu.scrollHeight;
        return balon;
    }

    function kaynakEkle(balon, kaynaklar) {
        if (!kaynaklar || !kaynaklar.length) return;
        var kutu = document.createElement("div");
        kutu.className = "kaynaklar";
        var baslik = document.createElement("span");
        baslik.className = "kaynak-baslik";
        baslik.textContent = "Kaynaklar:";
        kutu.appendChild(baslik);
        kaynaklar.forEach(function (k) {
            var cip = document.createElement("a");
            cip.className = "kaynak-cip";
            cip.target = "_blank";
            cip.rel = "noopener";
            cip.href = "/kaynak/" + k.kaynak_id + "?bolum=" + encodeURIComponent(k.bolum_bilgisi || "");
            cip.textContent = k.kaynak_adi + " — " + (k.bolum_bilgisi || "");
            kutu.appendChild(cip);
        });
        balon.appendChild(kutu);
    }

    function uyariEkle(balon, uyarilar) {
        (uyarilar || []).forEach(function (u) {
            var el = document.createElement("div");
            el.className = "uyari-kucuk";
            el.textContent = u;
            balon.appendChild(el);
        });
    }

    function geriBildirimEkle(balon, mesajId) {
        if (!girisli || !mesajId) return;
        var kutu = document.createElement("div");
        kutu.className = "geri-bildirim";
        kutu.dataset.mesajId = mesajId;
        kutu.innerHTML =
            '<button class="gb-buton gb-yararli" type="button">Yararlı</button>' +
            '<button class="gb-buton gb-yararsiz" type="button">Yararsız</button>' +
            '<div class="gb-aciklama-kutu gizli">' +
            '<textarea class="gb-aciklama" maxlength="300" placeholder="İsteğe bağlı açıklama (en fazla 300 karakter)"></textarea>' +
            '<button class="gb-gonder" type="button">Gönder</button></div>';
        balon.appendChild(kutu);
    }

    function yaziyorGoster(goster) {
        if (yaziyor) yaziyor.classList.toggle("gizli", !goster);
        if (mesajlarKutu) mesajlarKutu.scrollTop = mesajlarKutu.scrollHeight;
    }

    if (form) {
        form.addEventListener("submit", function (olay) {
            olay.preventDefault();
            var soru = soruKutusu.value.trim();
            if (!soru) return;
            var veri = new FormData();
            veri.append("soru", soru);
            if (aktifSohbetId) veri.append("sohbet_id", aktifSohbetId);
            soruKutusu.value = "";
            balonEkle("KULLANICI", soru);
            yaziyorGoster(true);
            var balon = null;
            fetch("/sohbet/yanit", { method: "POST", body: veri })
                .then(function (yanit) { return yanit.body.getReader(); })
                .then(function (okuyucu) {
                    var tampon = "";
                    function isle(satirlar) {
                        satirlar.forEach(function (satir) {
                            if (!satir.trim()) return;
                            var bol = satir.indexOf("\n");
                            var turSatiri = satir.slice(0, bol);
                            var veriSatiri = satir.slice(bol + 1);
                            if (veriSatiri.indexOf("data: ") !== 0) return;
                            var tur = turSatiri.replace("event: ", "").trim();
                            var icerik;
                            try { icerik = JSON.parse(veriSatiri.slice(6)); } catch (hata) { return; }
                            if (tur === "hata") {
                                balon = balonEkle("SISTEM", icerik.mesaj);
                            } else if (tur === "parca") {
                                if (!balon) balon = balonEkle("SISTEM", "");
                                balon.querySelector(".metin").textContent += icerik.metin;
                                mesajlarKutu.scrollTop = mesajlarKutu.scrollHeight;
                            } else if (tur === "sonuc") {
                                yaziyorGoster(false);
                                if (!balon) {
                                    balon = balonEkle("SISTEM", icerik.metin);
                                } else if (icerik.durum !== "YANIT") {
                                    balon.querySelector(".metin").textContent = icerik.metin;
                                }
                                if (icerik.sohbet_id) aktifSohbetId = icerik.sohbet_id;
                                kaynakEkle(balon, icerik.kaynaklar);
                                uyariEkle(balon, icerik.uyarilar);
                                geriBildirimEkle(balon, icerik.mesaj_id);
                                balon = null;
                            }
                        });
                    }
                    function oku() {
                        return okuyucu.read().then(function (sonuc) {
                            if (sonuc.done) return;
                            tampon += new TextDecoder().decode(sonuc.value, { stream: true });
                            var parcalar = tampon.split("\n\n");
                            tampon = parcalar.pop();
                            isle(parcalar);
                            return oku();
                        });
                    }
                    return oku();
                })
                .catch(function () {
                    yaziyorGoster(false);
                    balonEkle("SISTEM", "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.");
                })
                .finally(function () { yaziyorGoster(false); });
        });
    }

    if (yeniSohbetDugmesi) {
        yeniSohbetDugmesi.addEventListener("click", function () {
            if (!girisli && mesajlarKutu && mesajlarKutu.children.length > 0) {
                if (!window.confirm("Mevcut konuşmanız kalıcı olarak silinecek. Devam edilsin mi?")) {
                    return;
                }
            }
            window.location.href = "/sohbet/yeni";
        });
    }

    document.addEventListener("click", function (olay) {
        var dugme = olay.target.closest(".gb-buton, .gb-gonder");
        if (!dugme) return;
        var kutu = dugme.closest(".geri-bildirim");
        if (!kutu) return;
        var mesajId = parseInt(kutu.dataset.mesajId, 10);
        var aciklamaKutu = kutu.querySelector(".gb-aciklama-kutu");
        var tur = null;
        if (dugme.classList.contains("gb-yararli")) {
            tur = "YARARLI";
            aciklamaKutu.classList.add("gizli");
        } else if (dugme.classList.contains("gb-yararsiz")) {
            tur = "YARARSIZ";
            aciklamaKutu.classList.remove("gizli");
            return;
        } else if (dugme.classList.contains("gb-gonder")) {
            tur = "YARARSIZ";
        }
        var aciklama = kutu.querySelector(".gb-aciklama") ? kutu.querySelector(".gb-aciklama").value : null;
        fetch("/geri-bildirim", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mesaj_id: mesajId, tur: tur, aciklama: aciklama || null }),
        }).then(function (yanit) {
            if (yanit.ok) {
                kutu.innerHTML = '<span class="gb-teşekkür">Geri bildiriminiz için teşekkürler.</span>';
            }
        });
    });
})();
