import argparse
from pathlib import Path

from app.git_araclari import degisen_dosyalar, degisen_satirlar, dosya_icerigi, repo_koku
from app.llm import sor
from app.prompts import KOD_INCELEME_SISTEM
from app.reviewer import DIL_UZANTILARI, bulgulari_metne_cevir, inceleme_istegi_hazirla


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
        return

    for dosya in dosyalar:
        satirlar = degisen_satirlar(kok, dosya, a.staged)
        if not satirlar:
            continue
        kod = dosya_icerigi(kok, dosya, a.staged)
        istek, statik, _ = inceleme_istegi_hazirla(kod, Path(dosya).name, satirlar)

        print("=" * 60)
        print(f"{dosya}: {len(satirlar)} değişen satır, {len(statik)} statik bulgu")
        print(bulgulari_metne_cevir(statik))
        print("-" * 60)
        sor(istek, sistem=KOD_INCELEME_SISTEM, sicaklik=0.1)


if __name__ == "__main__":
    main()