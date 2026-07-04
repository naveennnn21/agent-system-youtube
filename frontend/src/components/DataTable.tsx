import type { ReactNode } from "react";

export type Column<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
};

type DataTableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
};

export function DataTable<T>({ columns, rows, getRowKey }: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-line text-left text-sm">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={`whitespace-nowrap px-3 py-2 text-xs font-semibold uppercase text-muted ${column.className || ""}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={getRowKey(row)} className="hover:bg-paper">
              {columns.map((column) => (
                <td key={column.key} className={`max-w-[280px] px-3 py-3 align-top text-ink ${column.className || ""}`}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
