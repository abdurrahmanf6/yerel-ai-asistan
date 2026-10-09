print("1) Script başladı")

import ollama
print("2) ollama kütüphanesi yüklendi")

print("3) Modele istek gönderiliyor (ilk seferde model belleğe yüklenirken 10-60 sn sürebilir)...")
stream = ollama.chat(
    model="qwen2.5-coder:7b",
    messages=[{"role": "user", "content": "OOP mantığı nedir?."}],
    stream=True,
)

for parca in stream:
    print(parca["message"]["content"], end="", flush=True)

print("\n4) Bitti")