import DOMPurify from "dompurify";
import { marked } from "marked";

/**
 * Markdown -> HTML seguro. El Markdown viene de un documento subido por el usuario: podría contener
 * HTML o scripts. DOMPurify elimina todo lo ejecutable antes de mostrarlo.
 */
export function renderMarkdown(md: string): string {
  const html = marked.parse(md, { async: false, gfm: true }) as string;
  return DOMPurify.sanitize(html);
}
