"""Yapılandırılmış (JSON) kod incelemesi.

Model bulguları JSON olarak üretir; diff filtresi, satır kontrolü,
tekrar temizliği ve rapor biçimi gibi kurallar Python'da uygulanır.
"""
import ast
import json
import re
import sys
import textwrap
from pathlib import Path

import ollama

from app.llm import VARSAYILAN_MODEL
from app.prompts import KOD, KOD_INCELEME_JSON_SISTEM
from app.reviewer import inceleme_istegi_hazirla

# Modelin uymak ZORUNDA olduğu çıktı şeması (Ollama structured outputs)
SEMA = {
    "type": "object",
    "properties": {
        "bulgular": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "satir": {"type": "integer"},
                    "onem": {"type": "string", "enum": ["kritik", "iyilestirme"]},
                    "baslik": {"type": "string"},
                    "neden": {"type": "string"},
                    "duzeltme": {"type": "string"},
                },
                "required": ["satir", "onem", "baslik", "neden", "duzeltme"],
            },
        },
        "puan": {"type": "integer"},
        "ozet": {"type": "string"},
    },
    "required": ["bulgular", "puan", "ozet"],
}

# Çince/Japonca karakterler ve tam genişlikli noktalama
CINCE = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")

# Kritik sayılan statik analiz kodları: S + rakam (güvenlik, örn. S605),
# F821 (tanımsız isim), kendi kurallarımız ve sözdizimi hataları.
# Not: SIM103 de "S" ile başlıyor, bu yüzden "S" + rakam şartı arıyoruz.
KRITIK_KOD = re.compile(r"^(S\d|F821|OZEL|SYNTAX)")


def sor_json(prompt, sistem, sema=SEMA, model=VARSAYILAN_MODEL, sicaklik=0.1, baglam=8192):
    yanit = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": sistem},
            {"role": "user", "content": prompt},
        ],
        format=sema,
        options={"temperature": sicaklik, "num_ctx": baglam},
    )
    icerik = yanit["message"]["content"]
    try:
        return json.loads(icerik)
    except json.JSONDecodeError:
        return {"bulgular": [], "puan": 0, "ozet": "Model geçerli JSON üretemedi."}


def _temiz_metin(metin):
    return CINCE.sub("", str(metin)).strip()


def _temiz_kod(metin, dil="Python"):
    """Backtick satırlarını atar. Python ise kodun gerçekten derlenebildiğini kontrol eder;
    derlenemiyorsa (örn. model kod yerine düz metin yazdıysa) düzeltmeyi boş bırakır."""
    satirlar = [s for s in str(metin).splitlines() if not s.strip().startswith(KOD)]
    kod = textwrap.dedent("\n".join(satirlar)).strip()
    if kod and dil == "Python":
        try:
            ast.parse(kod)
        except SyntaxError:
            return ""
    return kod


def _kapsamda(satir, degisen, tolerans=1):
    if not degisen:
        return True
    return any(abs(satir - d) <= tolerans for d in degisen)


def bulgulari_temizle(ham_bulgular, statik, satir_sayisi, degisen=None, dil="Python"):
    sonuc, gorulen = [], set()

    for b in ham_bulgular:
        try:
            satir = int(b.get("satir", 0))
        except (TypeError, ValueError):
            continue
        if not 1 <= satir <= satir_sayisi:
            continue  # dosyada olmayan satır = uydurma
        if not _kapsamda(satir, degisen):
            continue  # diff dışındaki satır: kural kodla uygulanıyor
        baslik = _temiz_metin(b.get("baslik", ""))
        anahtar = (satir, baslik.lower())
        if not baslik or anahtar in gorulen:
            continue  # boş veya tekrar eden bulgu
        gorulen.add(anahtar)
        sonuc.append({
            "satir": satir,
            "onem": "kritik" if b.get("onem") == "kritik" else "iyilestirme",
            "baslik": baslik,
            "neden": _temiz_metin(b.get("neden", "")),
            "duzeltme": _temiz_kod(b.get("duzeltme", ""), dil),
            "kaynak": "LLM",
        })

    # Statik analiz sonuçlarını modelin bulgularıyla birleştir (garanti taban)
    llm_bulgulari = list(sonuc)
    statik_satirlari = {s["satir"] for s in statik}
    for s in statik:
        statik_kritik = bool(KRITIK_KOD.match(s["kod"]))
        # Önce aynı satırdaki model bulgusunu ara. Yoksa ±1 satır kaymasına izin ver,
        # ama o komşu satırın kendi statik bulgusu varsa ona dokunma.
        eslesen = [b for b in llm_bulgulari if b["satir"] == s["satir"]] or [
            b for b in llm_bulgulari
            if abs(s["satir"] - b["satir"]) == 1 and b["satir"] not in statik_satirlari
        ]
        if eslesen:
            # Model aynı sorunu bulmuş: statik analiz kritik diyorsa önem kritik olur,
            # model ne derse desin (önem asla düşürülmez, sadece yükseltilir).
            if statik_kritik:
                for b in eslesen:
                    b["onem"] = "kritik"
            continue
        # Model atlamış: statik bulguyu doğrudan ekle
        sonuc.append({
            "satir": s["satir"],
            "onem": "kritik" if statik_kritik else "iyilestirme",
            "baslik": s["kod"],
            "neden": s["mesaj"],
            "duzeltme": "",
            "kaynak": "Statik analiz",
        })

    sonuc.sort(key=lambda b: (b["onem"] != "kritik", b["satir"]))
    return sonuc


def incele(kod, dosya_adi, degisen=None, model=VARSAYILAN_MODEL):
    """Tek giriş noktası: CLI, git diff ve arayüz bunu kullanır."""
    istek, statik, dil = inceleme_istegi_hazirla(kod, dosya_adi, degisen)
    ham = sor_json(istek, KOD_INCELEME_JSON_SISTEM, model=model)

    bulgular = bulgulari_temizle(
        ham.get("bulgular", []), statik, len(kod.splitlines()), degisen, dil
    )
    try:
        puan = max(0, min(10, int(ham.get("puan", 0))))
    except (TypeError, ValueError):
        puan = 0

    return {
        "dosya": dosya_adi,
        "dil": dil,
        "bulgular": bulgular,
        "statik": statik,
        "puan": puan,
        "ozet": _temiz_metin(ham.get("ozet", "")),
        "kritik_sayisi": sum(b["onem"] == "kritik" for b in bulgular),
    }


def markdown_rapor(sonuc):
    dil = sonuc["dil"].lower()
    cikti = []
    for onem, baslik in (("kritik", "Kritik Hatalar"), ("iyilestirme", "İyileştirme Önerileri")):
        cikti.append(f"## {baslik}")
        grup = [b for b in sonuc["bulgular"] if b["onem"] == onem]
        if not grup:
            cikti.append("Bulgu yok.\n")
        for b in grup:
            cikti.append(f"**Satır {b['satir']}** – {b['baslik']}  ({b['kaynak']})")
            cikti.append(f"Neden: {b['neden']}")
            if b["duzeltme"]:
                cikti.append(f"Düzeltme:\n{KOD}{dil}\n{b['duzeltme']}\n{KOD}")
            cikti.append("")
    cikti.append("## Genel Değerlendirme")
    cikti.append(f"{sonuc['puan']}/10 – {sonuc['ozet']}")
    return "\n".join(cikti)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Kullanım: python -m app.yapisal <dosya_yolu>")
        sys.exit(2)
    yol = Path(sys.argv[1])
    kod = yol.read_text(encoding="utf-8")
    print(f"İnceleniyor: {yol.name} (model çalışıyor, birkaç saniye sürebilir)...")
    sonuc = incele(kod, yol.name)
    print(markdown_rapor(sonuc))
    sys.exit(1 if sonuc["kritik_sayisi"] else 0)