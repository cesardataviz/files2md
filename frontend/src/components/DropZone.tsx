import { useRef, useState } from "react";

interface Props {
  accepts: string[];
  maxMb: number;
  maxFiles: number;
  onFiles: (files: File[]) => void;
}

const FRIENDLY_TYPES = "PDF, JPG, PNG, WebP, TIFF y Word";

export default function DropZone({ accepts, maxMb, maxFiles, onFiles }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function take(files: FileList | null) {
    const list = Array.from(files ?? []);
    if (list.length) onFiles(list);
  }

  return (
    <div
      className={`dropzone${dragging ? " is-dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        take(e.dataTransfer.files);
      }}
    >
      <span className="dropzone-pixels" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      <svg className="dropzone-icon" viewBox="0 0 48 48" aria-hidden="true">
        <path d="M13 6h15l9 9v27H13z" />
        <path d="M28 6v9h9" />
        <path d="M25 37V24m-5 5 5-5 5 5" />
      </svg>
      <p className="dropzone-title">Arrastra tus documentos aquí</p>
      <p className="dropzone-or">o</p>
      <button type="button" className="button button-secondary" onClick={() => input.current?.click()}>
        Elegir archivos
      </button>
      <p className="dropzone-hint">
        {FRIENDLY_TYPES} · hasta {maxFiles} archivos de {maxMb} MB cada uno
      </p>
      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept={accepts.map((e) => `.${e}`).join(",")}
        onChange={(e) => {
          take(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
