# Yerel Kod İnceleme Asistanı

Ollama üzerinde çalışan açık kaynaklı bir dil modeli (Qwen2.5-Coder 7B) ile **tamamen yerel** çalışan, Python tabanlı bir kod inceleme (code review) asistanı. Kod bilgisayardan dışarı çıkmaz; bulut API'si veya API anahtarı gerekmez.

Asistan; dil modelini, statik analizi (Ruff) ve projeye özel AST kurallarını birleştiren **hibrit** bir yapı kullanır. Model açıklama ve öneri üretir, kesinlik gerektiren kararları (satır numarası, önem derecesi, diff filtresi) ise Python kodu verir.

## Özellikler

- **Tam dosya incelemesi:** Bir dosyadaki hataları, güvenlik açıklarını ve iyileştirme fırsatlarını satır numarasıyla raporlar.
- **Git diff incelemesi:** Sadece değiştirilen satırları inceler (`git diff` / `--staged`).
- **Pre-commit hook:** Kritik bulgu içeren commit'leri otomatik olarak durdurur.
- **Web arayüzü (Streamlit):** Dosya yükleme, kod yapıştırma ve Git değişikliklerini inceleme sekmeleri.
- **Yapılandırılmış çıktı:** Model, JSON şemasına uyan çıktı üretir (Ollama structured outputs); rapor Python tarafından biçimlendirilir.
- **Gizlilik:** Her şey yerel makinede çalışır.

## Nasıl çalışır?

```
Kod / git diff
     │
     ├──► Ruff (statik analiz) ──────────┐
     ├──► Özel AST kuralları ────────────┤──► Statik bulgular
     │                                   │
     └──► Satır numaralandırma ──► Prompt (+ statik bulgular ipucu olarak)
                                         │
                                         ▼
                              Qwen2.5-Coder 7B (Ollama)
                              JSON şemasına uygun çıktı
                                         │
                                         ▼
                         Python kuralları (bulgulari_temizle)
                         • diff dışındaki bulguları at
                         • dosyada olmayan satırları at (uydurma)
                         • tekrarları ve Çince karakterleri temizle
                         • düzeltme önerisi derlenemiyorsa çıkar
                         • statik analiz "kritik" diyorsa önemi yükselt
                         • modelin atladığı statik bulguları ekle
                                         │
                                         ▼
                           Rapor (CLI / Streamlit / pre-commit)
```

## Geliştirme sürecinden öğrenilenler

Proje adım adım geliştirildi ve her adım, içine bilerek 6 hata konmuş bir test dosyasıyla (`ornekler/hatali.py`) ölçüldü:

| Yaklaşım | Bulunan hata (6 üzerinden) | Not |
|---|---|---|
| Sadece LLM, Türkçe prompt | ~2,5 | Yanlış satır numaraları, kritik hatalar "bulgu yok" |
| + İngilizce prompt, kontrol listesi, Ruff | 4 | Satırlar doğru, önerilerin bazıları hatalı |
| + Özel AST kuralları (Türkçe değişken adları) | 6 | Tüm hatalar bulundu |
| + JSON çıktı ve Python kuralları | 6 | Diff filtresi ve önem derecesi garanti altında |

Temel çıkarımlar:

1. **Küçük modeller "şunu yapma" talimatına her zaman uymaz.** Kesin olması gereken kurallar (diff dışını raporlama, önem derecesi) prompt ile değil kod ile uygulanmalı.
2. **Satır sayma gibi deterministik işler LLM'e bırakılmamalı.** Statik analiz araçları bu işi saniyenin altında ve hatasız yapar.
3. **Modelin önerileri doğrulanmalı.** Örneğin model Windows'ta çalışmayan `subprocess.run(["del", ...])` önerisi verdi; bu yüzden düzeltmeler derlenebilirlik kontrolünden geçirilir ve arayüzde uyarı gösterilir.
4. **Hook, araç bozulduğunda geliştiriciyi kilitlememeli.** Kritik bulgu için ayrı bir çıkış kodu (3) kullanılır; Ollama kapalıysa veya Python çökerse commit engellenmez, sadece uyarı verilir.

## Gereksinimler

- Windows 11 / Linux / macOS
- Python 3.10+
- [Ollama](https://ollama.com) 0.5 veya üzeri (structured outputs desteği için)
- Git
- Önerilen donanım: 8 GB VRAM'li bir GPU (geliştirme RTX 4060 8 GB üzerinde yapıldı)

## Kurulum

```powershell
git clone https://github.com/abdurrahmanf6/yerel-ai-asistan.git
cd yerel-ai-asistan

python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

ollama pull qwen2.5-coder:7b

# Pre-commit hook'u etkinleştir (isteğe bağlı)
git config core.hooksPath hooks
```

## Kullanım

**Tek dosya incelemesi:**

```powershell
python -m app.yapisal ornekler\hatali.py
```

**Git değişikliklerini inceleme:**

```powershell
python -m app.diff_review            # henüz git add yapılmamış değişiklikler
python -m app.diff_review --staged   # git add ile hazırlanmış değişiklikler
```

**Web arayüzü:**

```powershell
streamlit run ui.py
```

**Pre-commit hook:** `git config core.hooksPath hooks` komutundan sonra her `git commit` otomatik incelenir. Kritik bulgu varsa commit durdurulur. Acil durumlarda atlamak için: `git commit --no-verify`.

### Çıkış kodları (`app.diff_review`)

| Kod | Anlamı |
|---|---|
| 0 | Kritik bulgu yok |
| 2 | İnceleme yapılamadı (Ollama kapalı, git hatası vb.) |
| 3 | Kritik bulgu var |

## Proje yapısı

```
yerel-ai-asistan/
├── app/
│   ├── llm.py               # Ollama ile konuşan katman (metin / akış)
│   ├── prompts.py           # Sistem promptları ve istek şablonları
│   ├── ozel_kontroller.py   # AST tabanlı özel kurallar (gizli bilgi, len() ile bölme)
│   ├── reviewer.py          # Ruff entegrasyonu, satır numaralandırma, istek hazırlama
│   ├── yapisal.py           # JSON çıktı, bulgu temizleme kuralları, rapor
│   ├── git_araclari.py      # git diff ayrıştırma (değişen satırlar)
│   └── diff_review.py       # Git değişikliklerini inceleyen CLI
├── hooks/
│   └── pre-commit           # Kritik bulguda commit'i durduran hook
├── ornekler/
│   └── hatali.py            # Bilerek hatalı test dosyası
├── ui.py                    # Streamlit arayüzü
└── requirements.txt
```

> `ornekler/hatali.py` **bilerek** hatalar içerir (command injection, gömülü şifre, mutable default argüman vb.). Asistanı test etmek için kullanılır, gerçek kodda örnek alınmamalıdır.

## Sınırlamalar

- 7B model temiz kodda bazen gerçek olmayan iyileştirme önerileri üretebilir. Bu öneriler `(LLM)` etiketiyle gösterilir ve commit'i engellemez; sadece statik analizle desteklenen veya model tarafından kritik bulunan sorunlar engeller.
- Statik analiz ve özel AST kuralları şu an yalnızca Python için çalışır. Diğer diller sadece LLM ile incelenir.
- Çok büyük dosyalar modelin bağlam penceresini (`num_ctx = 8192`) aşabilir.

## Yol haritası

- [ ] Büyük dosyalar için parçalara bölerek (chunking) inceleme
- [ ] Farklı modelleri aynı test dosyasıyla karşılaştıran değerlendirme betiği
- [ ] Diğer diller için statik analiz desteği (ör. ESLint)
- [ ] Bulgu sonuçlarını JSON / HTML rapor olarak dışa aktarma

## Teknolojiler

Python · Ollama · Qwen2.5-Coder 7B · Ruff · Python `ast` · Streamlit · Git hooks
