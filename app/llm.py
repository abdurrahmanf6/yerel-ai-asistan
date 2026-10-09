import ollama

VARSAYILAN_MODEL = "qwen2.5-coder:7b"


def sor(prompt, sistem="Sen yardımsever bir asistansın.",
        model=VARSAYILAN_MODEL, akis=True, sicaklik=0.2, baglam=8192):
    """Modele soru sorar ve yanıtın tamamını metin olarak döndürür."""
    mesajlar = [
        {"role": "system", "content": sistem},   # modelin rolü / kuralları
        {"role": "user", "content": prompt},     # asıl istek
    ]
    secenekler = {
        "temperature": sicaklik,  # düşük değer: daha tutarlı, daha az uydurma
        "num_ctx": baglam,        # bağlam penceresi: uzun metinlerin kesilmemesi için
    }

    if not akis:
        yanit = ollama.chat(model=model, messages=mesajlar, options=secenekler)
        return yanit["message"]["content"]

    tam_metin = ""
    for parca in ollama.chat(model=model, messages=mesajlar,
                             options=secenekler, stream=True):
        metin = parca["message"]["content"]
        print(metin, end="", flush=True)
        tam_metin += metin
    print()
    return tam_metin

def sor_akis(prompt, sistem="Sen yardımsever bir asistansın.",
             model=VARSAYILAN_MODEL, sicaklik=0.2, baglam=8192):
    """Yanıtı parça parça döndüren generator (arayüzler için)."""
    mesajlar = [
        {"role": "system", "content": sistem},
        {"role": "user", "content": prompt},
    ]
    for parca in ollama.chat(model=model, messages=mesajlar,
                             options={"temperature": sicaklik, "num_ctx": baglam},
                             stream=True):
        yield parca["message"]["content"]
        
if __name__ == "__main__":
    sor(
        "Python'da fonksiyonlarda neden mutable default argüman (örn. def f(x=[])) "
        "kullanılmamalı? 3 cümleyle anlat.",
        sistem="Sen deneyimli bir Python eğitmenisin. Kısa, doğru ve tekrarsız cevap ver.",
    )