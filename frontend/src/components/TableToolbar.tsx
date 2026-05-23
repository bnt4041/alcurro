import { FormEvent } from "react";

export interface FilterOption {
  value: string;
  label: string;
}

interface Props {
  search: string;
  onSearchChange: (v: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  filters?: {
    label: string;
    value: string;
    options: FilterOption[];
    onChange: (v: string) => void;
  }[];
  extra?: React.ReactNode;
}

export default function TableToolbar({
  search,
  onSearchChange,
  onSubmit,
  placeholder = "Buscar…",
  filters = [],
  extra,
}: Props) {
  const handle = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form className="table-toolbar" onSubmit={handle}>
      <input
        type="search"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder={placeholder}
        className="search-input"
      />
      {filters.map((f) => (
        <label key={f.label} className="filter-label">
          {f.label}
          <select value={f.value} onChange={(e) => f.onChange(e.target.value)}>
            <option value="">Todos</option>
            {f.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      ))}
      <button type="submit" className="btn">
        Buscar
      </button>
      {extra}
    </form>
  );
}
