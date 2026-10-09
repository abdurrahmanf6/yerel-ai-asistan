from pathlib import Path

import streamlit as st

from app.git_araclari import degisen_dosyalar, degisen_satirlar, dosya_icerigi, repo_koku
from app.llm import VARSAYILAN_MODEL
from app.reviewer import DIL_UZANTILARI
from app.yapisal import incele

st.set_page_config(page_title="Yerel Kod İnceleme Asistanı", layout="wide")
st.title("Yerel Kod İnceleme Asistanı")
st.caption(f"Model: {VARSAYILAN_MODEL} · Tamamen yerel çalışır, kodun bilgisayarından çıkmaz.")


def sonucu_goster(sonuc, kod=None):
    dil = sonuc["dil"].lower()
    k1, k2, k3 = st.columns(3)
    k1.metric("Kritik", sonuc["kritik_sayisi"])
    k2.metric("İyileştirme", len(sonuc["bulgular"]) - sonuc["kritik_sayisi"])
    k3.metric("Puan", f"{sonuc['puan']}/10")
    if sonuc["ozet"]:
        st.write(sonuc["ozet"])

    if not sonuc["bulgular"]:
        st.success("Bulgu yok.")
    for b in sonuc["bulgular"]:
        ikon = "🔴" if b["onem"] == "kritik" else "🟡"
        with st.expander(f"{ikon} Satır {b['satir']} – {b['baslik']}",
                         expanded=b["onem"] == "kritik"):
            st.write(b["neden"])
            st.caption(f"Kaynak: {b['kaynak']}")
            if b["duzeltme"]:
                st.code(b["duzeltme"], language=dil)

    if kod is not None:
        with st.expander("Kodu göster"):
            st.code(kod, language=dil, line_numbers=True)


st.info("Öneriler otomatik üretilir; uygulamadan önce kontrol et.")
sekme_dosya, sekme_git = st.tabs(["Dosya incele", "Git değişiklikleri"])

with sekme_dosya:
    yuklenen = st.file_uploader(
        "Bir kod dosyası seç", type=[u.lstrip(".") for u in DIL_UZANTILARI]
    )
    yapistirilan = st.text_area("...veya Python kodunu buraya yapıştır", height=250)

    kod, dosya_adi = None, None
    if yuklenen is not None:
        kod = yuklenen.getvalue().decode("utf-8", errors="replace")
        dosya_adi = yuklenen.name
    elif yapistirilan.strip():
        kod, dosya_adi = yapistirilan, "yapistirilan.py"

    if st.button("İncele", type="primary", disabled=kod is None, key="dosya_btn"):
        with st.spinner("Model inceliyor..."):
            sonuc = incele(kod, dosya_adi)
        sonucu_goster(sonuc, kod)

with sekme_git:
    repo = st.text_input("Git deposunun yolu", value=".")
    staged = st.checkbox("Sadece 'git add' yapılmış değişiklikler (--staged)")

    if st.button("Değişiklikleri incele", type="primary", key="git_btn"):
        try:
            kok = repo_koku(repo)
            dosyalar = [d for d in degisen_dosyalar(kok, staged)
                        if Path(d).suffix.lower() in DIL_UZANTILARI]
        except RuntimeError as e:
            st.error(f"Git hatası: {e}")
            st.stop()

        if not dosyalar:
            st.success("İncelenecek değişiklik yok.")
        for dosya in dosyalar:
            satirlar = degisen_satirlar(kok, dosya, staged)
            if not satirlar:
                continue
            st.subheader(f"{dosya}  ·  {len(satirlar)} değişen satır")
            with st.spinner(f"{dosya} inceleniyor..."):
                kod = dosya_icerigi(kok, dosya, staged)
                sonuc = incele(kod, Path(dosya).name, satirlar)
            sonucu_goster(sonuc)
            st.divider()