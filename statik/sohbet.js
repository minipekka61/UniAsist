(function () {
    "use strict";
    var mesajlarKutu = document.getElementById("mesajlar");
    var yaziyor = document.getElementById("yaziyor");
    var form = document.getElementById("soru-formu");
    var soruKutusu = document.getElementById("soru");
    var yeniSohbetDugmesi = document.getElementById("yeni-sohbet");
    var dersFiltre = document.getElementById("ders-filtre");
    var aktifSohbetId = window.uniasistSohbetId || null;
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

    function kaynakcaEkle(balon, kaynaklar) {
        if (!kaynaklar || !kaynaklar.length) return;
        var kutu = document.createElement("div");
        kutu.className = "kaynakca";
        var dugme = document.createElement("button");
        dugme.type = "button";
        dugme.className = "kaynakca-dugme";
        dugme.textContent = "Kaynakçalar";
        kutu.appendChild(dugme);
        var liste = document.createElement("div");
        liste.className = "kaynakca-liste gizli";
        kaynaklar.forEach(function (k) {
            var cip = document.createElement("a");
            cip.className = "kaynak-cip";
            cip.target = "_blank";
            cip.rel = "noopener";
            cip.href = "/kaynak/" + k.kaynak_id + "?bolum=" + encodeURIComponent(k.bolum_bilgisi || "");
            cip.textContent = k.kaynak_adi + " — " + (k.bolum_bilgisi || "");
            liste.appendChild(cip);
        });
        kutu.appendChild(liste);
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
            if (dersFiltre && dersFiltre.value) veri.append("ders_id", dersFiltre.value);
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
                                if (icerik.sohbet_id) {
                                    aktifSohbetId = icerik.sohbet_id;
                                    if (!window.uniasistSohbetId) {
                                        window.location.href = "/sohbet?sohbet_id=" + aktifSohbetId;
                                    }
                                }
                                kaynakcaEkle(balon, icerik.kaynaklar);
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
            window.location.href = "/sohbet/yeni";
        });
    }

    document.addEventListener("click", function (olay) {
        var kaynakcaDugme = olay.target.closest(".kaynakca-dugme");
        if (kaynakcaDugme) {
            var kaynakca = kaynakcaDugme.closest(".kaynakca");
            var liste = kaynakca ? kaynakca.querySelector(".kaynakca-liste") : null;
            if (liste) liste.classList.toggle("gizli");
            return;
        }

        var adlandirDugme = olay.target.closest(".sohbet-adlandir-buton");
        if (adlandirDugme) {
            var satir = adlandirDugme.closest(".sohbet-satir");
            if (!satir) return;
            var sohbetId = satir.dataset.sohbetId;
            var link = satir.querySelector(".sohbet-baslik-link");
            if (!link || satir.querySelector(".sohbet-ad-kutu")) return;
            var kutu = document.createElement("div");
            kutu.className = "sohbet-ad-kutu";
            var giris = document.createElement("input");
            giris.type = "text";
            giris.className = "sohbet-ad-giris";
            giris.maxLength = 100;
            giris.value = link.textContent;
            var kaydet = document.createElement("button");
            kaydet.type = "button";
            kaydet.className = "buton-kucuk";
            kaydet.textContent = "Kaydet";
            kutu.appendChild(giris);
            kutu.appendChild(kaydet);
            link.classList.add("gizli");
            satir.insertBefore(kutu, satir.querySelector(".sohbet-satir-butonlar"));
            giris.focus();
            giris.select();
            function adlandir() {
                var yeniAd = giris.value.trim();
                if (!yeniAd) {
                    kutu.remove();
                    link.classList.remove("gizli");
                    return;
                }
                var veri = new FormData();
                veri.append("baslik", yeniAd);
                fetch("/sohbet/" + sohbetId + "/ad", { method: "POST", body: veri })
                    .then(function () { window.location.reload(); });
            }
            kaydet.addEventListener("click", adlandir);
            giris.addEventListener("keydown", function (e) {
                if (e.key === "Enter") adlandir();
                if (e.key === "Escape") {
                    kutu.remove();
                    link.classList.remove("gizli");
                }
            });
            return;
        }

        var dugme = olay.target.closest(".gb-buton, .gb-gonder");
        if (!dugme) return;
        var kutu2 = dugme.closest(".geri-bildirim");
        if (!kutu2) return;
        var mesajId = parseInt(kutu2.dataset.mesajId, 10);
        var aciklamaKutu = kutu2.querySelector(".gb-aciklama-kutu");
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
        var aciklama = kutu2.querySelector(".gb-aciklama") ? kutu2.querySelector(".gb-aciklama").value : null;
        fetch("/geri-bildirim", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mesaj_id: mesajId, tur: tur, aciklama: aciklama || null }),
        }).then(function (yanit) {
            if (yanit.ok) {
                kutu2.innerHTML = '<span class="gb-tesekkur">Geri bildiriminiz için teşekkürler.</span>';
            }
        });
    });
})();
