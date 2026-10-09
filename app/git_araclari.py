import re
import subprocess

# "@@ -10,2 +12,3 @@" satırından yeni dosyadaki başlangıç (12) ve adet (3) bilgisini alır
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


def git(repo, *args):
    sonuc = subprocess.run(
        ["git", "-c", "core.quotepath=off", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    if sonuc.returncode != 0:
        raise RuntimeError(sonuc.stderr.strip())
    return sonuc.stdout


def repo_koku(yol="."):
    return git(yol, "rev-parse", "--show-toplevel").strip()


def degisen_dosyalar(repo, staged=False):
    """Eklenen/değiştirilen dosyaların listesi (silinenler hariç)."""
    args = ["diff", "--name-only", "--diff-filter=AM"]
    if staged:
        args.append("--cached")
    return [d for d in git(repo, *args).splitlines() if d.strip()]


def degisen_satirlar(repo, dosya, staged=False):
    """Dosyada eklenen/değiştirilen satır numaralarını küme olarak döndürür."""
    args = ["diff", "-U0"]          # -U0: bağlam satırı olmadan, sadece değişiklikler
    if staged:
        args.append("--cached")
    diff = git(repo, *args, "--", dosya)

    satirlar = set()
    for m in HUNK.finditer(diff):
        baslangic = int(m.group(1))
        adet = int(m.group(2)) if m.group(2) is not None else 1
        satirlar.update(range(baslangic, baslangic + adet))  # adet=0 ise sadece silme vardır
    return satirlar


def dosya_icerigi(repo, dosya, staged=False):
    """staged ise 'git add' ile hazırlanmış hâli, değilse diskteki hâli."""
    if staged:
        return git(repo, "show", f":{dosya}")
    with open(f"{repo}/{dosya}", encoding="utf-8") as f:
        return f.read()