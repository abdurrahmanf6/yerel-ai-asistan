import os

def ortalama_hesapla(sayilar):
    toplam = 0
    for s in sayilar:
        toplam += s
    return toplam / len(sayilar)

def kullanici_bul(kullanicilar, isim, sonuc=[]):
    for k in kullanicilar:
        if k["isim"] == isim:
            sonuc.append(k)
    return sonuc

def dosya_sil(dosya_adi):
    os.system("del " + dosya_adi)

def sifre_kontrol(girilen):
    sifre = "admin123"
    if girilen == sifre:
        return True
    else:
        return False

def dosya_oku(yol):
    f = open(yol)
    veri = f.read()
    return veri
