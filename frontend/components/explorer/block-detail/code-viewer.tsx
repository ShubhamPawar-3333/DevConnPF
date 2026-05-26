"use client";

import { useMemo } from "react";

interface CodeViewerProps {
  code: string;
  language: string;
}

/**
 * Displays source code with line numbers and basic syntax highlighting.
 * Uses a lightweight pre/code approach with line numbers.
 */
export function CodeViewer({ code, language }: CodeViewerProps) {
  const lines = useMemo(() => code.split("\n"), [code]);

  const lineNumberWidth = useMemo(
    () => String(lines.length).length,
    [lines.length]
  );

  return (
    <div className="overflow-auto rounded-md border bg-muted/30">
      <pre className="text-sm leading-relaxed">
        <code className={`language-${language}`}>
          <table className="w-full border-collapse">
            <tbody>
              {lines.map((line, index) => (
                <tr key={index} className="hover:bg-muted/50">
                  <td
                    className="select-none border-r border-border px-3 py-0.5 text-right text-xs text-muted-foreground"
                    style={{ minWidth: `${lineNumberWidth + 2}ch` }}
                    aria-hidden="true"
                  >
                    {index + 1}
                  </td>
                  <td className="px-4 py-0.5 whitespace-pre">
                    {line || "\u00A0"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </code>
      </pre>
    </div>
  );
}
