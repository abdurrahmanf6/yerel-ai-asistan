import json
import subprocess
import sys
from pathlib import Path

from app.llm import sor
from app.ozel_kontroller import ozel_kontrolleri_calistir
from app.prompts import KOD_INCELEME_SISTEM, kod_inceleme_istegi

DIL_UZANTILARI = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".java": "Java", ".cs": "C#", ".cpp": "C++", ".c": "C",
}


def satir_numarala(kod):
    satirlar = kod.splitlines()
    genislik = len(str(len(satirlar)))
    return "\n".join(
        f"{i:>{genislik}} | {satir}" for i, satir in enumerate(satirlar, start=1)
    )


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


def inceleme_istegi_hazirla(kod, dosya_adi):
    """Hem CLI hem arayüz bunu kullanır: (istek, statik_bulgular, dil) döndürür."""
    dil = DIL_UZANTILARI.get(Path(dosya_adi).suffix.lower(), "kod")
    statik = statik_analiz(kod, dosya_adi)
    istek = kod_inceleme_istegi(
        dosya_adi, satir_numarala(kod), dil, bulgulari_metne_cevir(statik)
    )
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