import json
import subprocess
import sys
from pathlib import Path

from app.llm import sor
from app.ozel_kontroller import ozel_kontrolleri_calistir
from app.prompts import DIFF_TALIMATI, KOD_INCELEME_SISTEM, kod_inceleme_istegi

DIL_UZANTILARI = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".java": "Java", ".cs": "C#", ".cpp": "C++", ".c": "C",
}


def satir_numarala(kod, isaretli=None, baglam=None):
    """Satırlara numara ekler. isaretli satırların başına '>>' koyar.
    baglam verilirse sadece işaretli satırlar ve çevresindeki ±baglam satır gösterilir."""
    isaretli = isaretli or set()
    satirlar = kod.splitlines()
    genislik = len(str(len(satirlar)))

    if isaretli and baglam is not None:
        gosterilecek = {i for s in isaretli for i in range(s - baglam, s + baglam + 1)}
    else:
        gosterilecek = set(range(1, len(satirlar) + 1))

    cikti, onceki = [], 0
    for i, satir in enumerate(satirlar, start=1):
        if i not in gosterilecek:
            continue
        if i != onceki + 1:
            cikti.append("   ...")
        isaret = ">>" if i in isaretli else "  "
        cikti.append(f"{isaret} {i:>{genislik}} | {satir}")
        onceki = i
    return "\n".join(cikti)


def ruff_calistir(kod, dosya_adi):
    """Kodu stdin üzerinden Ruff'a verir (diske yazmaya gerek yok)."""
    sonuc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--isolated",
         "--output-format=json", "--select", "E,F,B,S,SIM",
         "--stdin-filename", dosya_adi, "-"],
        input=kod, capture_output=True, text=True, encoding="utf-8",
    )
    try:
        ham = json.loads(sonuc.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return [
        {"satir": b["location"]["row"], "kod": b["code"], "mesaj": b["message"]}
        for b in ham
    ]


def statik_analiz(kod, dosya_adi):
    if not dosya_adi.lower().endswith(".py"):
        return []
    bulgular = ruff_calistir(kod, dosya_adi) + ozel_kontrolleri_calistir(kod)
    return sorted(bulgular, key=lambda b: b["satir"])


def bulgulari_metne_cevir(bulgular):
    if not bulgular:
        return "No issues found by the static analyzer."
    return "\n".join(f"- Line {b['satir']}: [{b['kod']}] {b['mesaj']}" for b in bulgular)


def inceleme_istegi_hazirla(kod, dosya_adi, degisen_satirlar=None):
    """Hem CLI hem arayüz bunu kullanır: (istek, statik_bulgular, dil) döndürür.
    degisen_satirlar verilirse sadece o satırlar incelenir (git diff modu)."""
    dil = DIL_UZANTILARI.get(Path(dosya_adi).suffix.lower(), "kod")
    statik = statik_analiz(kod, dosya_adi)

    if degisen_satirlar:
        statik = [b for b in statik if b["satir"] in degisen_satirlar]
        numarali = satir_numarala(kod, degisen_satirlar, baglam=5)
    else:
        numarali = satir_numarala(kod)

    istek = kod_inceleme_istegi(dosya_adi, numarali, dil, bulgulari_metne_cevir(statik))
    if degisen_satirlar:
        istek += "\n" + DIFF_TALIMATI
    return istek, statik, dil


def dosya_incele(yol):
    dosya = Path(yol)
    if not dosya.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {dosya}")
    kod = dosya.read_text(encoding="utf-8")
    if not kod.strip():
        raise ValueError("Dosya boş.")

    istek, statik, dil = inceleme_istegi_hazirla(kod, dosya.name)
    print(f"İnceleniyor: {dosya.name} ({len(kod.splitlines())} satır, {dil})")
    print(f"Statik analiz: {len(statik)} bulgu")
    print(bulgulari_metne_cevir(statik))
    print("-" * 60)
    return sor(istek, sistem=KOD_INCELEME_SISTEM, sicaklik=0.1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Kullanım: python -m app.reviewer <dosya_yolu>")
        sys.exit(1)
    dosya_incele(sys.argv[1])