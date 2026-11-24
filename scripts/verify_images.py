"""Verifica que cada imagen de data/imagenes.yaml responda 200, sea imagen y supere el tamaño mínimo.

Uso: python scripts/verify_images.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
import yaml

RAIZ = Path(__file__).resolve().parent.parent
TAMANO_MINIMO_BYTES = 30_000
AGENTE = "MiProximoCarroBot/1.0 (+https://github.com/ingsamuelorozco/MiProximoCarro)"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    imgs = yaml.safe_load((RAIZ / "data" / "imagenes.yaml").read_text(encoding="utf-8"))["imagenes"]
    fallas = 0
    with httpx.Client(headers={"User-Agent": AGENTE}, follow_redirects=True, timeout=20) as cli:
        for img in imgs:
            estado, tipo, tam = None, "", 0
            for intento in range(3):
                try:
                    r = cli.head(img["url"])
                    if r.status_code == 405:
                        r = cli.get(img["url"])
                    estado, tipo = r.status_code, r.headers.get("content-type", "")
                    tam = int(r.headers.get("content-length") or len(r.content or b""))
                    if estado == 200:
                        break
                except httpx.HTTPError as e:
                    tipo = str(e)
                time.sleep(2 * (intento + 1))
            ok = estado == 200 and tipo.startswith("image/") and tam >= TAMANO_MINIMO_BYTES
            fallas += not ok
            print(f"{'OK ' if ok else 'ERR'} {img['id']}: {estado} {tipo} {tam} bytes")
    print(f"\n{len(imgs) - fallas}/{len(imgs)} imágenes válidas")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
