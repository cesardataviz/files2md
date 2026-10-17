import { extensionOf, formatBytes } from "../lib/messages";

interface Props {
  file: File;
  onChange?: () => void;
  changeLabel?: string;
}

export default function FileCard({ file, onChange, changeLabel = "Cambiar" }: Props) {
  const ext = extensionOf(file.name);
  return (
    <div className="file-card">
      <span className="file-badge" aria-hidden="true">
        {ext.slice(0, 4) || "?"}
      </span>
      <div className="file-info">
        <p className="file-name" title={file.name}>
          {file.name}
        </p>
        <p className="file-size">{formatBytes(file.size)}</p>
      </div>
      {onChange && (
        <button type="button" className="button button-ghost" onClick={onChange}>
          {changeLabel}
        </button>
      )}
    </div>
  );
}
