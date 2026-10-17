import { Fragment } from "react";

/** Nombre de archivo con cortes de línea suaves después de "_", "-" y ".": evita partir "pdf" en "pd / f". */
export default function Breakable({ text }: { text: string }) {
  const parts = text.split(/(?<=[_\-.])/);
  return (
    <>
      {parts.map((part, i) => (
        <Fragment key={i}>
          {part}
          {i < parts.length - 1 && <wbr />}
        </Fragment>
      ))}
    </>
  );
}
