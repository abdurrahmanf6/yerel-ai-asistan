import argparse
import sys
from pathlib import Path

from app.git_araclari import degisen_dosyalar, degisen_satirlar, dosya_icerigi, repo_koku
from app.reviewer import DIL_UZANTILARI
from app.yapisal import incele, markdown_rapor

# Çıkış kodları: 0 = temiz, 3 = kritik bulgu var, 2 = inceleme yapılamadı.
# Kritik için 1 yerine 3 kullanıyoruz: Python çökerse de 1 döner, karışmasın.
KRITIK_VAR = 3


def main():
    p = argparse.ArgumentParser(description="Git değişikliklerini yerel LLM ile inceler")
    p.add_argument("repo", nargs="?", default=".", help="Git deposunun yolu")
    p.add_argument("--staged", action="store_true",
                   help="Sadece 'git add' ile hazırlanmış değişiklikleri incele")
    a = p.parse_args()

    kok = repo_koku(a.repo)
    dosyalar = [d for d in degisen_dosyalar(kok, a.staged)
                if Path(d).suffix.lower() in DIL_UZANTILARI]

    if not dosyalar:
        print("İncelenecek değişiklik yok.")
        return 0

    toplam_kritik = 0
    for dosya in dosyalar:
        satirlar = degisen_satirlar(kok, dosya, a.staged)
        if not satirlar:
            continue
        kod = dosya_icerigi(kok, dosya, a.staged)

        print("=" * 60)
        print(f"{dosya}: {len(satirlar)} değişen satır (model çalışıyor...)")
        print("=" * 60)
        sonuc = incele(kod, Path(dosya).name, satirlar)
        print(markdown_rapor(sonuc))
        toplam_kritik += sonuc["kritik_sayisi"]

    print("=" * 60)
    print(f"TOPLAM KRİTİK BULGU: {toplam_kritik}")
    return KRITIK_VAR if toplam_kritik else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # Ollama kapalı, git hatası vb.
        print(f"İnceleme yapılamadı: {e}")
        sys.exit(2)