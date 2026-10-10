/** Renders chemistry strings (Unicode subscripts from API; legacy <sub> tags). */

function replaceScriptTags(text: string): string {
  return text
    .replace(/<sub>\s*([^<]+?)\s*<\/sub>/gi, (_, inner: string) =>
      inner.replace(/[0-9]/g, (d) => '₀₁₂₃₄₅₆₇₈₉'[Number(d)]),
    )
    .replace(/<sup>\s*([^<]+?)\s*<\/sup>/gi, (_, inner: string) =>
      inner.replace(/[0-9+\-]/g, (ch) => {
        const map: Record<string, string> = {
          '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
          '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
          '+': '⁺', '-': '⁻',
        }
        return map[ch] ?? ch
      }),
    )
    .replace(/<\/?sub>/gi, '')
    .replace(/<\/?sup>/gi, '')
}

export function ChemistryText({ text }: { text: string }) {
  const safe = replaceScriptTags(text)
  return <span style={{ whiteSpace: 'pre-wrap' }}>{safe}</span>
}
