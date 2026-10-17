# Benchmark de motores

Objetivo: decidir **con datos** qué motor usar para cada tipo de documento, y saber cuánto cuesta en tiempo.

## Uso rápido

Desde la raíz del repo:

```bash
pip install -e "backend[dev,bench]"
python benchmarks/make_synthetic.py      # 6 escaneos y 9 fotos de celular sintéticos + su Markdown correcto
python benchmarks/run.py                 # todos los motores disponibles
python benchmarks/run.py --engines ocr   # solo uno
```

Salida: una línea por documento, un resumen por motor y categoría, y un CSV en `benchmarks/results/`.

```
motor    categoría      docs  éxito     CER     WER  s/pág
ocr      escaneos          6   100%   0.000   0.000  2.667
ocr      fotos             9   100%   0.000   0.000  2.524
```

### Resultado del preprocesamiento de fotos (16-oct-2026)

Ablación sobre las 9 fotos sintéticas (hoja sobre mesa, perspectiva, reflejo, sombra, JPG comprimido):

| Preprocesamiento | CER medio | Peor caso |
|---|---|---|
| Ninguno | 0,248 | 0,780 |
| Solo igualar luz | 0,196 | 0,694 |
| Solo ampliar | 0,323 | 1,000 |
| Solo perspectiva | 0,393 | 0,499 |
| Perspectiva + luz | 0,002 | 0,014 |
| **Perspectiva + ampliar + luz** (por defecto) | **0,000** | **0,000** |

Lección: sin preprocesar, el OCR no detectaba zonas enteras con reflejo (la confianza seguía alta, ~90). Ninguna
técnica sola basta; funciona la combinación. Con una foto real de un libro, la cobertura de palabras impresas
subió de 90 % a 98 %; el texto manuscrito sigue fuera del alcance de Tesseract.

> Los sintéticos son **más fáciles** que un escaneo real. Sirven para comprobar que todo funciona,
> no para afirmar qué tan bueno es un motor.

## Con tus propios documentos

```
benchmarks/
  dataset/
    escaneados/contrato_01.pdf          # la carpeta es la "categoría" en el resumen
    tablas/reporte_ventas.pdf
  ground_truth/
    escaneados/contrato_01.md           # mismo nombre y carpeta, extensión .md
    tablas/reporte_ventas.md
```

1. Elige entre 10 y 50 documentos variados: escaneos buenos y malos, tablas, dos columnas, formularios.
2. Escribe a mano el Markdown correcto de cada uno (el *ground truth*). Es lo más lento y lo más valioso:
   sin él solo se mide el tiempo.
3. Corre `python benchmarks/run.py`.

**Privacidad:** `dataset/`, `ground_truth/` y `results/` están en `.gitignore`. Nunca subas documentos
personales a este repo público. Si quieres publicar resultados, copia el resumen a mano y revisa que no
incluya nombres de archivo sensibles.

## Métricas

| Métrica | Qué mide | Cómo leerla |
|---|---|---|
| **CER** | Errores de carácter / caracteres de la referencia | 0.02 = 2 de cada 100 caracteres mal |
| **WER** | Errores de palabra / palabras de la referencia | Más severa: un carácter mal arruina la palabra |
| **s/pág** | Segundos por página | Depende del hardware: compara motores en la misma máquina |
| **éxito** | % de documentos que terminaron sin error | |

CER y WER se calculan sobre el texto **sin sintaxis Markdown**: la estructura (títulos, tablas) se evaluará
con métricas propias (pendiente: TEDS para tablas y orden de lectura). Pueden superar 1.0 si el motor
inventa texto, lo cual sirve para detectar alucinaciones.

Implementación: [`backend/app/eval/metrics.py`](../backend/app/eval/metrics.py).

## Pendiente

- Dataset real con ground truth.
- Métricas de estructura: TEDS (tablas), jerarquía de títulos, orden de lectura.
- Comparar con Docling y un VLM local cuando estén disponibles.
