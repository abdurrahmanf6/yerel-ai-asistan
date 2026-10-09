import streamlit as st

from app.llm import VARSAYILAN_MODEL, sor_akis
from app.prompts import KOD_INCELEME_SISTEM
from app.reviewer import DIL_UZANTILARI, inceleme_istegi_hazirla

st.set_page_config(page_title="Yerel Kod İnceleme Asistanı", layout="wide")
st.title("Yerel Kod İnceleme Asistanı")
st.caption(f"Model: {VARSAYILAN_MODEL} · Tamamen yerel çalışır, kodun bilgisayarından çıkmaz.")

sekme_dosya, sekme_yapistir = st.tabs(["Dosya yükle", "Kod yapıştır"])
with sekme_dosya:
    yuklenen = st.file_uploader(
        "Bir kod dosyası seç", type=[u.lstrip(".") for u in DIL_UZANTILARI]
    )
with sekme_yapistir:
    yapistirilan = st.text_area("Python kodunu buraya yapıştır", height=300)

kod, dosya_adi = None, None
if yuklenen is not None:
    kod = yuklenen.getvalue().decode("utf-8", errors="replace")
    dosya_adi = yuklenen.name
elif yapistirilan.strip():
    kod, dosya_adi = yapistirilan, "yapistirilan.py"

if st.button("İncele", type="primary", disabled=kod is None):
    istek, statik, dil = inceleme_istegi_hazirla(kod, dosya_adi)

    sol, sag = st.columns([1, 1])
    with sol:
        st.subheader(dosya_adi)
        st.code(kod, language=dil.lower(), line_numbers=True)
    with sag:
        st.subheader(f"Statik analiz ({len(statik)} bulgu)")
        if statik:
            st.dataframe(statik, hide_index=True)
        else:
            st.success("Statik analiz sorun bulmadı.")

        st.subheader("Yapay zeka incelemesi")
        st.info("Öneriler yapay zeka tarafından üretilmiştir, uygulamadan önce kontrol et.")
        with st.spinner("Model düşünüyor..."):
            st.write_stream(sor_akis(istek, sistem=KOD_INCELEME_SISTEM, sicaklik=0.1))