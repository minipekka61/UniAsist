(function () {
    "use strict";

    var CEREZ_ADI = "uniasist_tema";
    var dugme = document.getElementById("tema-dugme");
    var kok = document.documentElement;

    function cerezAl(ad) {
        var parcalar = document.cookie.split(";");
        for (var i = 0; i < parcalar.length; i++) {
            var parca = parcalar[i].trim();
            if (parca.indexOf(ad + "=") === 0) {
                return parca.substring(ad.length + 1);
            }
        }
        return null;
    }

    function cerezYaz(ad, deger) {
        document.cookie =
            ad + "=" + deger + "; path=/; max-age=31536000; samesite=lax";
    }

    function temayiUygula(tema) {
        kok.setAttribute("data-tema", tema);
    }

    if (!cerezAl(CEREZ_ADI)) {
        if (
            window.matchMedia &&
            window.matchMedia("(prefers-color-scheme: dark)").matches
        ) {
            temayiUygula("koyu");
        }
    }

    if (dugme) {
        dugme.addEventListener("click", function () {
            var yeni = kok.getAttribute("data-tema") === "koyu" ? "acik" : "koyu";
            temayiUygula(yeni);
            cerezYaz(CEREZ_ADI, yeni);
        });
    }
})();
