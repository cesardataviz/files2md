// Elemento distintivo: una hoja hecha de "píxeles" (los cuadrados del logo) que una línea de escaneo
// convierte en líneas de texto. Representa literalmente lo que hace el OCR.
import { useEffect, useState } from "react";

const ROWS = 15;
const TOP = 34;
const ROW_GAP = 13;
const LEFT = 26;
const WIDTH = 148;
// Longitudes de línea fijas (fracción del ancho): parecen un párrafo real y no "saltan" entre renders.
const LENGTHS = [0.62, 0, 1, 0.94, 0.98, 0.71, 0, 1, 0.9, 0.97, 0.86, 0.45, 0, 0.92, 0.66];
const SQUARE = 4;
const STEP = 6;

function noise(i: number, j: number): number {
  const x = Math.sin(i * 12.9898 + j * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

interface Props {
  active: boolean; // false: escaneo detenido (movimiento reducido o terminado)
}

export default function ScanPage({ active }: Props) {
  const [scan, setScan] = useState(0.45);

  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!active || reduce) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      setScan(((now - start) / 2600) % 1.08); // 8% de pausa al final de cada pasada
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active]);

  const scanY = TOP - 8 + Math.min(scan, 1) * (ROWS * ROW_GAP + 4);

  return (
    <svg className="scan-page" viewBox="0 0 200 250" role="img" aria-label="Leyendo el documento">
      <rect className="scan-sheet" x="8" y="8" width="184" height="234" rx="10" />
      <g className="scan-corner">
        <rect x="16" y="16" width="5" height="5" rx="1" />
        <rect x="23" y="16" width="5" height="5" rx="1" opacity="0.7" />
        <rect x="16" y="23" width="5" height="5" rx="1" opacity="0.45" />
      </g>
      {LENGTHS.map((len, i) => {
        if (len === 0) return null;
        const y = TOP + i * ROW_GAP;
        const width = WIDTH * len;
        const isHeading = i === 0;
        if (y + 4 < scanY) {
          return (
            <rect
              key={i}
              className={isHeading ? "scan-heading" : "scan-line"}
              x={LEFT}
              y={y - (isHeading ? 1 : 0)}
              width={width}
              height={isHeading ? 7 : 5}
              rx="2.5"
            />
          );
        }
        const count = Math.floor(width / STEP);
        return (
          <g key={i} className="scan-pixels">
            {Array.from({ length: count }, (_, j) => {
              const n = noise(i, j);
              return n < 0.18 ? null : (
                <rect key={j} x={LEFT + j * STEP} y={y} width={SQUARE} height={SQUARE} rx="0.8" opacity={0.25 + n * 0.6} />
              );
            })}
          </g>
        );
      })}
      {scan <= 1 && (
        <g className="scan-beam" transform={`translate(0 ${scanY})`}>
          <rect x="14" y="-9" width="172" height="10" className="scan-glow" />
          <rect x="14" y="0" width="172" height="2" rx="1" />
        </g>
      )}
    </svg>
  );
}
