import { useEffect, useState } from "react";
import ProductIcon from "./ProductIcon";

type Theme = "light" | "dark";

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem("files2md_theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* almacenamiento bloqueado: usar preferencia del sistema */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function Header() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("files2md_theme", theme);
    } catch {
      /* sin persistencia: el tema vuelve al del sistema al recargar */
    }
  }, [theme]);

  const next = theme === "dark" ? "light" : "dark";

  return (
    <header className="topbar">
      <a className="brand" href="/" aria-label="files2md, inicio">
        <ProductIcon />
        <span className="brand-name">
          files<span className="brand-two">2</span>md
        </span>
      </a>
      <a className="by-softcom" href="https://softcom.com.pe" target="_blank" rel="noreferrer">
        por <img src="/softcom.png" alt="" width={16} height={16} /> Softcom
      </a>
      <div className="topbar-actions">
        <span className="privacy-pill" title="Los archivos no se envían a internet">
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M4.5 7V5a3.5 3.5 0 0 1 7 0v2M3.5 7h9v7h-9z" />
          </svg>
          Se procesa en tu computadora
        </span>
        <button
          type="button"
          className="icon-button"
          onClick={() => setTheme(next)}
          aria-label={next === "dark" ? "Activar modo oscuro" : "Activar modo claro"}
        >
          {theme === "dark" ? (
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="4.5" />
              <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
